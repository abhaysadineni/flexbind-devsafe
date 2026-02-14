"""Step C — Lightweight interface scoring proxy.

Scores the binder–target interface using four geometric/chemical terms:

1. Contact score   — number of inter-chain Cβ contacts within a cutoff.
2. Clash score     — penalty for inter-chain atom pairs closer than 2.0 Å.
3. H-bond proxy   — count of donor–acceptor backbone atom pairs (N…O) within
                     2.5–3.5 Å across the interface.
4. SASA burial     — fraction of binder interface residues whose Cα becomes
                     more buried upon complexation (approximated via neighbour
                     count change).

All terms are combined into a single composite score (higher = better binding).
"""

from __future__ import annotations

import numpy as np
from Bio.PDB.Structure import Structure

from app.models import StateScore


# Amino-acid hydrophobicity scale (Kyte-Doolittle, normalised 0–1)
KD_SCALE: dict[str, float] = {
    "ILE": 1.00, "VAL": 0.93, "LEU": 0.84, "PHE": 0.62, "CYS": 0.56,
    "MET": 0.42, "ALA": 0.40, "GLY": 0.18, "THR": 0.16, "SER": 0.13,
    "TRP": 0.11, "TYR": 0.07, "PRO": 0.05, "HIS": 0.00, "GLU": 0.00,
    "GLN": 0.00, "ASP": 0.00, "ASN": 0.00, "LYS": 0.00, "ARG": 0.00,
}


def _get_all_coords(structure: Structure) -> tuple[np.ndarray, list[dict]]:
    """Return Nx3 coordinate array and metadata list for all atoms in model 0."""
    coords = []
    info = []
    model = structure[0]
    for chain in model:
        for residue in chain:
            for atom in residue:
                coords.append(atom.get_vector().get_array())
                info.append({
                    "chain": chain.id,
                    "resi": residue.id[1],
                    "resn": residue.get_resname(),
                    "atom": atom.name,
                    "element": atom.element,
                })
    return np.array(coords) if coords else np.zeros((0, 3)), info


def _get_cb_coords(structure: Structure) -> tuple[np.ndarray, list[dict]]:
    """Return Cβ (or Cα for GLY) coordinates and metadata."""
    coords = []
    info = []
    model = structure[0]
    for chain in model:
        for residue in chain:
            atom_name = "CB" if "CB" in residue else ("CA" if "CA" in residue else None)
            if atom_name is None:
                continue
            atom = residue[atom_name]
            coords.append(atom.get_vector().get_array())
            info.append({
                "chain": chain.id,
                "resi": residue.id[1],
                "resn": residue.get_resname(),
            })
    return np.array(coords) if coords else np.zeros((0, 3)), info


def score_interface(
    target_structure: Structure,
    binder_structure: Structure,
    contact_cutoff: float = 8.0,
    clash_cutoff: float = 2.0,
    hbond_dist_range: tuple[float, float] = (2.5, 3.5),
) -> StateScore:
    """Score the interface between target and binder structures.

    Returns a StateScore with individual terms and a composite.
    """
    # ── Contact score (Cβ–Cβ) ───────────────────────────────────────────────
    t_cb, t_info = _get_cb_coords(target_structure)
    b_cb, b_info = _get_cb_coords(binder_structure)

    if t_cb.shape[0] == 0 or b_cb.shape[0] == 0:
        return StateScore(
            state_index=0, contact_score=0, clash_score=0,
            hbond_proxy=0, sasa_burial=0, composite=0,
        )

    # Pairwise distances (target × binder)
    diff = t_cb[:, None, :] - b_cb[None, :, :]  # (T, B, 3)
    dists = np.sqrt(np.sum(diff**2, axis=2))     # (T, B)

    contacts = int(np.sum(dists < contact_cutoff))
    contact_score = min(contacts / max(len(b_info), 1) * 10.0, 100.0)

    # ── Clash score (all-atom) ──────────────────────────────────────────────
    t_all, t_all_info = _get_all_coords(target_structure)
    b_all, b_all_info = _get_all_coords(binder_structure)

    if t_all.shape[0] > 0 and b_all.shape[0] > 0:
        # Subsample for speed if structures are large
        max_atoms = 3000
        if t_all.shape[0] > max_atoms:
            idx = np.linspace(0, t_all.shape[0] - 1, max_atoms, dtype=int)
            t_all = t_all[idx]
        if b_all.shape[0] > max_atoms:
            idx = np.linspace(0, b_all.shape[0] - 1, max_atoms, dtype=int)
            b_all = b_all[idx]

        diff_all = t_all[:, None, :] - b_all[None, :, :]
        dists_all = np.sqrt(np.sum(diff_all**2, axis=2))
        n_clashes = int(np.sum(dists_all < clash_cutoff))
        clash_score = max(0.0, 1.0 - n_clashes * 0.5)  # penalise clashes
    else:
        clash_score = 1.0

    # ── H-bond proxy (backbone N…O pairs across interface) ──────────────────
    hbond_count = 0
    # Use backbone N/O atoms only
    t_donors = np.array([c for c, i in zip(t_all.tolist(), t_all_info) if i.get("atom") == "N"]) if len(t_all_info) > 0 else np.zeros((0, 3))
    b_acceptors = np.array([c for c, i in zip(b_all.tolist(), b_all_info) if i.get("atom") == "O"]) if len(b_all_info) > 0 else np.zeros((0, 3))

    if len(t_donors) > 0 and len(b_acceptors) > 0:
        t_donors = np.array(t_donors)
        b_acceptors = np.array(b_acceptors)
        diff_hb = t_donors[:, None, :] - b_acceptors[None, :, :]
        dists_hb = np.sqrt(np.sum(diff_hb**2, axis=2))
        hbond_count += int(np.sum((dists_hb > hbond_dist_range[0]) & (dists_hb < hbond_dist_range[1])))

    # Reverse (binder N → target O)
    b_donors = np.array([c for c, i in zip(b_all.tolist(), b_all_info) if i.get("atom") == "N"]) if len(b_all_info) > 0 else np.zeros((0, 3))
    t_acceptors = np.array([c for c, i in zip(t_all.tolist(), t_all_info) if i.get("atom") == "O"]) if len(t_all_info) > 0 else np.zeros((0, 3))

    if len(b_donors) > 0 and len(t_acceptors) > 0:
        b_donors = np.array(b_donors)
        t_acceptors = np.array(t_acceptors)
        diff_hb2 = b_donors[:, None, :] - t_acceptors[None, :, :]
        dists_hb2 = np.sqrt(np.sum(diff_hb2**2, axis=2))
        hbond_count += int(np.sum((dists_hb2 > hbond_dist_range[0]) & (dists_hb2 < hbond_dist_range[1])))

    hbond_proxy = min(hbond_count / 5.0, 10.0)

    # ── SASA burial proxy ───────────────────────────────────────────────────
    # Approximate: for each binder Cβ, count how many target Cβ are within 10 Å
    if t_cb.shape[0] > 0 and b_cb.shape[0] > 0:
        close_counts = np.sum(dists < 10.0, axis=0)  # per binder residue
        burial_fraction = float(np.mean(close_counts > 0))
        sasa_burial = burial_fraction * 10.0
    else:
        sasa_burial = 0.0

    # ── Composite ───────────────────────────────────────────────────────────
    composite = (
        contact_score * 0.35
        + clash_score * 10.0 * 0.20
        + hbond_proxy * 0.25
        + sasa_burial * 0.20
    )

    return StateScore(
        state_index=0,
        contact_score=round(contact_score, 2),
        clash_score=round(clash_score, 3),
        hbond_proxy=round(hbond_proxy, 2),
        sasa_burial=round(sasa_burial, 2),
        composite=round(composite, 3),
    )


def score_ensemble(
    target_structure: Structure,
    ensemble: list[Structure],
) -> list[StateScore]:
    """Score each ensemble member against the target. Returns a list of StateScores."""
    scores: list[StateScore] = []
    for i, binder in enumerate(ensemble):
        ss = score_interface(target_structure, binder)
        ss.state_index = i
        scores.append(ss)
    return scores
