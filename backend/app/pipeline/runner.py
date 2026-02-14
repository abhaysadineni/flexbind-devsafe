"""Pipeline runner — orchestrates Steps A through F.

Called by the Celery worker.  All state is persisted to the job directory
on disk so the API can serve progress updates and final results.
"""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

from Bio.PDB import PDBParser

from app import config
from app.models import (
    BinderType,
    DesignResult,
    DevelopabilityBreakdown,
    JobReport,
    JobStatus,
    RunMode,
    StateScore,
)
from app.utils import append_log, job_dir, set_progress, set_status, read_meta, write_meta

from app.pipeline.preprocess import clean_pdb, get_flexible_residues, extract_sequence
from app.pipeline.ensemble import generate_ensemble, save_ensemble
from app.pipeline.scoring import score_ensemble
from app.pipeline.sequence_design import design_sequences
from app.pipeline.developability import compute_developability


def run_pipeline(job_id: str) -> None:
    """Execute the full FlexBind pipeline for a given job.

    Reads configuration from jobs/<job_id>/meta.json, writes results
    back to the job directory, and updates status/progress as it goes.
    """
    jdir = job_dir(job_id)
    meta = read_meta(job_id)
    parser = PDBParser(QUIET=True)

    mode = RunMode(meta["mode"])
    binder_type = BinderType(meta["binder_type"])
    seed = int(meta.get("seed", config.DEFAULT_SEED))
    no_glyco = bool(meta.get("no_glycosylation", True))
    flex_spec = meta.get("flexible_residues") or None
    cutoff = float(meta.get("interface_distance", config.INTERFACE_DISTANCE_CUTOFF))

    is_deep = mode == RunMode.DEEP
    ensemble_samples = config.DEEP_ENSEMBLE_SIZE if is_deep else config.FAST_ENSEMBLE_SIZE
    ensemble_clusters = max(3, ensemble_samples // 3)
    n_designs = config.DEEP_DESIGN_CANDIDATES if is_deep else config.FAST_DESIGN_CANDIDATES
    beam_width = 5 if is_deep else 3

    try:
        set_status(job_id, JobStatus.RUNNING, "Pipeline started")

        # ── Step A: Preprocess ──────────────────────────────────────────────
        set_progress(job_id, 0.05, "Step A: Preprocessing PDB files…")

        target_raw = jdir / "target.pdb"
        binder_raw = jdir / "binder.pdb"
        target_clean = jdir / "target_clean.pdb"
        binder_clean = jdir / "binder_clean.pdb"

        if not target_raw.exists() or not binder_raw.exists():
            raise FileNotFoundError("Missing target.pdb or binder.pdb in job directory")

        target_struct = clean_pdb(target_raw, target_clean)
        binder_struct = clean_pdb(binder_raw, binder_clean)

        flex_residues = get_flexible_residues(
            target_struct, binder_struct, binder_type.value, flex_spec, cutoff
        )
        if not flex_residues:
            append_log(job_id, "WARNING: No flexible residues detected — using all binder residues")
            model = binder_struct[0]
            for chain in model:
                for residue in chain:
                    flex_residues.append((chain.id, residue.id[1]))

        append_log(job_id, f"  Flexible residues: {len(flex_residues)} positions")
        set_progress(job_id, 0.10, "Step A: Done")

        # ── Step B: Ensemble generation ─────────────────────────────────────
        set_progress(job_id, 0.15, "Step B: Generating conformational ensemble…")

        ensemble = generate_ensemble(
            binder_structure=binder_struct,
            target_structure=target_struct,
            flex_residues=flex_residues,
            n_samples=ensemble_samples,
            n_clusters=ensemble_clusters,
            seed=seed,
            magnitude=0.6 if not is_deep else 1.0,
        )

        ens_dir = jdir / "ensemble"
        ens_dir.mkdir(exist_ok=True)
        ens_paths = save_ensemble(ensemble, ens_dir)
        append_log(job_id, f"  Ensemble: {len(ensemble)} representative states saved")
        set_progress(job_id, 0.35, "Step B: Done")

        # ── Step C: Score ensemble ──────────────────────────────────────────
        set_progress(job_id, 0.40, "Step C: Scoring ensemble against target…")

        state_scores = score_ensemble(target_struct, ensemble)
        append_log(
            job_id,
            f"  Scores — mean composite: {sum(s.composite for s in state_scores)/len(state_scores):.2f}"
        )
        set_progress(job_id, 0.50, "Step C: Done")

        # ── Step D: Sequence design ─────────────────────────────────────────
        set_progress(job_id, 0.55, "Step D: Running sequence design…")

        design_results = design_sequences(
            target=target_struct,
            binder=binder_struct,
            ensemble=ensemble,
            designable_positions=flex_residues,
            n_candidates=n_designs,
            beam_width=beam_width,
            seed=seed,
            no_glycosylation=no_glyco,
        )
        append_log(job_id, f"  Generated {len(design_results)} design candidates")
        set_progress(job_id, 0.75, "Step D: Done")

        # ── Step E: Developability ──────────────────────────────────────────
        set_progress(job_id, 0.80, "Step E: Computing developability scores…")

        dev_score = compute_developability(binder_struct, seed=seed)
        append_log(job_id, f"  Developability: {dev_score.composite}/100 ({dev_score.flag})")
        set_progress(job_id, 0.90, "Step E: Done")

        # ── Step F: Compile results ─────────────────────────────────────────
        set_progress(job_id, 0.92, "Step F: Compiling results…")

        # Build ranked design list
        designs: list[DesignResult] = []
        for rank, d in enumerate(design_results, 1):
            designs.append(DesignResult(
                rank=rank,
                sequence=d["sequence"],
                mutations=d["mutations"],
                mean_score=d["mean_score"],
                worst_score=d["worst_score"],
                robustness=d["robustness"],
                developability_score=dev_score.composite,
                developability_flag=dev_score.flag,
                per_state_scores=[
                    StateScore(**s.model_dump()) if isinstance(s, StateScore) else s
                    for s in d["per_state_scores"]
                ],
            ))

        # Write report.json
        report = JobReport(
            job_id=job_id,
            status=JobStatus.DONE,
            binder_type=binder_type,
            mode=mode,
            seed=seed,
            ensemble_size=len(ensemble),
            designs=designs,
            developability=dev_score,
        )
        report_path = jdir / "report.json"
        with open(report_path, "w") as f:
            f.write(report.model_dump_json(indent=2))

        # Write designs.csv
        csv_path = jdir / "designs.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "rank", "sequence", "mutations", "mean_score", "worst_score",
                "robustness", "developability_score", "developability_flag",
            ])
            for d in designs:
                writer.writerow([
                    d.rank, d.sequence, d.mutations, d.mean_score, d.worst_score,
                    d.robustness, d.developability_score, d.developability_flag,
                ])

        # Write FASTA
        fasta_path = jdir / "designs.fasta"
        with open(fasta_path, "w") as f:
            for d in designs:
                f.write(f">design_{d.rank:03d} mutations={d.mutations} robustness={d.robustness}\n")
                f.write(d.sequence + "\n")

        # Build ZIP
        zip_path = jdir / "results.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(report_path, "report.json")
            zf.write(csv_path, "designs.csv")
            zf.write(fasta_path, "designs.fasta")
            zf.write(target_clean, "target_clean.pdb")
            zf.write(binder_clean, "binder_clean.pdb")
            for ep in ens_paths:
                zf.write(ep, f"ensemble/{ep.name}")

        set_progress(job_id, 1.0, "Pipeline complete")
        set_status(job_id, JobStatus.DONE, "All steps completed successfully")

    except Exception as exc:
        set_status(job_id, JobStatus.FAILED, str(exc))
        append_log(job_id, f"FATAL ERROR: {exc}")
        raise
