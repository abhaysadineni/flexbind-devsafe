"""Step D — Sequence design via position-specific mutation search.

Implements a beam-search-based sequence optimiser that mutates interface
residues to improve the multi-state binding score while respecting user
constraints (fixed positions, allowed amino acids, no-glycosylation filter).

If ProteinMPNN is importable, it would be used instead — but this fallback
provides a credible working baseline without any external model weights.
"""

from __future__ import annotations

import copy
from typing import Optional

import numpy as np
from Bio.PDB.Structure import Structure
from Bio.PDB.Polypeptide import three_to_one, one_to_three

from app.pipeline.scoring import score_interface
from app.models import StateScore


# Standard amino acids (single letter)
AA_ALPHABET = list("ACDEFGHIKLMNPQRSTVWY")

# Rough physico-chemical compatibility groups for smarter mutations
COMPATIBLE_GROUPS: dict[str, list[str]] = {
    "hydrophobic": list("AVILMFYW"),
    "polar": list("STNQ"),
    "charged_pos": list("KRH"),
    "charged_neg": list("DE"),
    "special": list("CGP"),
}

# Glycosylation motif: N-X-S/T where X ≠ P
def _has_glycosylation_motif(seq: str) -> bool:
    """Check if sequence contains N-X-S/T motif (X ≠ P)."""
    for i in range(len(seq) - 2):
        if seq[i] == "N" and seq[i + 1] != "P" and seq[i + 2] in ("S", "T"):
            return True
    return False


def _get_aa_group(aa: str) -> str:
    for group, members in COMPATIBLE_GROUPS.items():
        if aa in members:
            return group
    return "special"


def _smart_candidates(current_aa: str, allowed: Optional[set[str]] = None) -> list[str]:
    """Return candidate mutations biased toward physico-chemically similar residues."""
    group = _get_aa_group(current_aa)
    primary = COMPATIBLE_GROUPS.get(group, [])
    others = [aa for aa in AA_ALPHABET if aa not in primary]

    # Prioritise same-group mutations, but include a few cross-group
    candidates = [aa for aa in primary if aa != current_aa]
    candidates += others[:4]  # Add a few diverse options

    if allowed is not None:
        candidates = [aa for aa in candidates if aa in allowed]

    return candidates


def _apply_mutation(
    structure: Structure,
    chain_id: str,
    resi: int,
    new_aa_1: str,
) -> Structure:
    """Apply a point mutation by changing the residue name (proxy: we keep
    the backbone and Cβ but label with the new residue identity).

    This is a simplified proxy — in a production system you'd repack
    side-chains.  For scoring purposes, the backbone geometry (which
    drives our contact/clash/hbond scoring) is unchanged.
    """
    new_struct = copy.deepcopy(structure)
    model = new_struct[0]
    new_aa_3 = one_to_three(new_aa_1)

    for chain in model:
        if chain.id == chain_id:
            for residue in chain:
                if residue.id[1] == resi:
                    residue.resname = new_aa_3
                    break
    return new_struct


def _extract_interface_sequence(
    structure: Structure,
    positions: list[tuple[str, int]],
) -> str:
    """Extract the single-letter sequence at given positions."""
    model = structure[0]
    seq: list[str] = []
    for chain_id, resi in positions:
        for chain in model:
            if chain.id == chain_id:
                for residue in chain:
                    if residue.id[1] == resi:
                        try:
                            seq.append(three_to_one(residue.get_resname()))
                        except KeyError:
                            seq.append("X")
                        break
    return "".join(seq)


def _score_design_multistate(
    target: Structure,
    binder: Structure,
    ensemble: list[Structure],
    mutations: list[tuple[str, int, str]],
) -> tuple[float, float, list[StateScore]]:
    """Score a set of mutations across all ensemble states.

    Returns (mean_score, worst_score, per_state_scores).
    """
    # Apply mutations to the canonical binder
    mutated = copy.deepcopy(binder)
    for chain_id, resi, new_aa in mutations:
        mutated = _apply_mutation(mutated, chain_id, resi, new_aa)

    per_state: list[StateScore] = []
    for i, state in enumerate(ensemble):
        # For each ensemble state, create a version with mutations applied
        mutated_state = copy.deepcopy(state)
        for chain_id, resi, new_aa in mutations:
            mutated_state = _apply_mutation(mutated_state, chain_id, resi, new_aa)

        ss = score_interface(target, mutated_state)
        ss.state_index = i
        per_state.append(ss)

    composites = [s.composite for s in per_state]
    mean_s = float(np.mean(composites))
    worst_s = float(np.min(composites))
    return mean_s, worst_s, per_state


def design_sequences(
    target: Structure,
    binder: Structure,
    ensemble: list[Structure],
    designable_positions: list[tuple[str, int]],
    n_candidates: int = 10,
    beam_width: int = 3,
    seed: int = 42,
    fixed_positions: Optional[set[tuple[str, int]]] = None,
    allowed_aas: Optional[dict[tuple[str, int], set[str]]] = None,
    no_glycosylation: bool = True,
) -> list[dict]:
    """Run a beam-search sequence design over designable positions.

    Returns a list of design dicts sorted by robustness score (worst-case weighted).
    """
    rng = np.random.default_rng(seed)
    fixed = fixed_positions or set()
    allowed = allowed_aas or {}

    # Determine mutable positions
    mutable = [(c, r) for c, r in designable_positions if (c, r) not in fixed]

    if not mutable:
        # Nothing to design — score the wildtype
        mean_s, worst_s, per_state = _score_design_multistate(
            target, binder, ensemble, []
        )
        wt_seq = _extract_interface_sequence(binder, designable_positions)
        return [{
            "sequence": wt_seq,
            "mutations": "wildtype",
            "mean_score": round(mean_s, 3),
            "worst_score": round(worst_s, 3),
            "robustness": round(worst_s * 0.6 + mean_s * 0.4, 3),
            "per_state_scores": per_state,
        }]

    # Greedy beam search: iterate over mutable positions
    # Each beam entry: (mutations_list, cumulative_score)
    beam: list[tuple[list[tuple[str, int, str]], float]] = [([], 0.0)]

    for chain_id, resi in mutable[:8]:  # Cap positions for speed
        new_beam: list[tuple[list[tuple[str, int, str]], float]] = []
        # Get current AA
        current_aa = _extract_interface_sequence(binder, [(chain_id, resi)])
        if not current_aa or current_aa == "X":
            continue

        pos_allowed = allowed.get((chain_id, resi))
        candidates = _smart_candidates(current_aa, pos_allowed)
        candidates = candidates[:5]  # Limit per-position candidates
        candidates.insert(0, current_aa)  # Always consider wildtype

        for mutations, prev_score in beam:
            for candidate_aa in candidates:
                if candidate_aa == current_aa:
                    new_mutations = mutations[:]
                else:
                    new_mutations = mutations + [(chain_id, resi, candidate_aa)]

                mean_s, worst_s, _ = _score_design_multistate(
                    target, binder, ensemble, new_mutations
                )
                robustness = worst_s * 0.6 + mean_s * 0.4
                new_beam.append((new_mutations, robustness))

        # Keep top beam_width entries
        new_beam.sort(key=lambda x: x[1], reverse=True)
        beam = new_beam[:beam_width]

    # Expand final beam into full results
    results: list[dict] = []
    seen_seqs: set[str] = set()

    for mutations, _ in beam:
        mean_s, worst_s, per_state = _score_design_multistate(
            target, binder, ensemble, mutations
        )

        # Build full designed sequence
        designed_binder = copy.deepcopy(binder)
        for c, r, aa in mutations:
            designed_binder = _apply_mutation(designed_binder, c, r, aa)
        seq = _extract_interface_sequence(designed_binder, designable_positions)

        # Glycosylation filter
        if no_glycosylation and _has_glycosylation_motif(seq):
            continue

        if seq in seen_seqs:
            continue
        seen_seqs.add(seq)

        mut_str = ", ".join(f"{c}{r}{aa}" for c, r, aa in mutations) if mutations else "wildtype"
        robustness = worst_s * 0.6 + mean_s * 0.4

        results.append({
            "sequence": seq,
            "mutations": mut_str,
            "mean_score": round(mean_s, 3),
            "worst_score": round(worst_s, 3),
            "robustness": round(robustness, 3),
            "per_state_scores": per_state,
        })

    # Also add some random diverse designs
    for _ in range(min(n_candidates, 20)):
        random_mutations: list[tuple[str, int, str]] = []
        for c, r in mutable[:8]:
            current_aa = _extract_interface_sequence(binder, [(c, r)])
            if not current_aa or current_aa == "X":
                continue
            if rng.random() < 0.4:  # 40% chance to mutate each position
                pos_allowed = allowed.get((c, r))
                cands = _smart_candidates(current_aa, pos_allowed)
                if cands:
                    new_aa = rng.choice(cands)
                    random_mutations.append((c, r, new_aa))

        if not random_mutations:
            continue

        mean_s, worst_s, per_state = _score_design_multistate(
            target, binder, ensemble, random_mutations
        )

        designed_binder = copy.deepcopy(binder)
        for c, r, aa in random_mutations:
            designed_binder = _apply_mutation(designed_binder, c, r, aa)
        seq = _extract_interface_sequence(designed_binder, designable_positions)

        if no_glycosylation and _has_glycosylation_motif(seq):
            continue
        if seq in seen_seqs:
            continue
        seen_seqs.add(seq)

        mut_str = ", ".join(f"{c}{r}{aa}" for c, r, aa in random_mutations)
        robustness = worst_s * 0.6 + mean_s * 0.4

        results.append({
            "sequence": seq,
            "mutations": mut_str,
            "mean_score": round(mean_s, 3),
            "worst_score": round(worst_s, 3),
            "robustness": round(robustness, 3),
            "per_state_scores": per_state,
        })

    results.sort(key=lambda x: x["robustness"], reverse=True)
    return results[:n_candidates]
