"""Step E — Developability, aggregation risk, and self-association scoring.

Computes five risk terms and combines them into a DevelopabilityScore [0–100]:

1. Hydrophobic patch score — fraction of surface-exposed hydrophobic residues.
2. Net charge & pI — using amino-acid pKa values.
3. Beta-sheet propensity — average β-sheet propensity of the sequence.
4. Self-dock risk proxy — dock the binder against a copy of itself and score
   the interface stickiness.

The composite score is 100 (best) minus weighted penalties.
"""

from __future__ import annotations

import copy

import numpy as np
from Bio.PDB.Structure import Structure
from Bio.PDB.Polypeptide import three_to_one

from app.models import DevelopabilityBreakdown
from app.pipeline.scoring import score_interface

# ── Constants ────────────────────────────────────────────────────────────────

# Kyte-Doolittle hydrophobicity (higher = more hydrophobic)
HYDROPHOBICITY: dict[str, float] = {
    "I": 4.5, "V": 4.2, "L": 3.8, "F": 2.8, "C": 2.5,
    "M": 1.9, "A": 1.8, "G": -0.4, "T": -0.7, "S": -0.8,
    "W": -0.9, "Y": -1.3, "P": -1.6, "H": -3.2, "E": -3.5,
    "Q": -3.5, "D": -3.5, "N": -3.5, "K": -3.9, "R": -4.5,
}

# Chou-Fasman β-sheet propensity (normalised)
BETA_PROPENSITY: dict[str, float] = {
    "V": 1.70, "I": 1.60, "Y": 1.47, "F": 1.38, "W": 1.37,
    "L": 1.30, "T": 1.19, "C": 1.19, "Q": 1.10, "M": 1.05,
    "R": 0.93, "N": 0.89, "H": 0.87, "A": 0.83, "S": 0.75,
    "G": 0.75, "K": 0.74, "D": 0.54, "P": 0.55, "E": 0.37,
}

# pKa values for pI calculation
PKA_NTERM = 9.69
PKA_CTERM = 2.34
PKA_SIDE: dict[str, float] = {
    "D": 3.65, "E": 4.25, "C": 8.18, "Y": 10.07,
    "H": 6.00, "K": 10.53, "R": 12.48,
}


# ── Utility functions ────────────────────────────────────────────────────────

def _extract_full_sequence(structure: Structure) -> str:
    """Get concatenated single-letter sequence from all chains."""
    seq_parts: list[str] = []
    model = structure[0]
    for chain in model:
        for residue in chain:
            try:
                seq_parts.append(three_to_one(residue.get_resname()))
            except KeyError:
                continue
    return "".join(seq_parts)


def _count_residue(seq: str, aa: str) -> int:
    return seq.count(aa)


def _net_charge_at_ph(seq: str, ph: float = 7.4) -> float:
    """Calculate net charge at a given pH."""
    charge = 0.0
    # N-terminus (positive)
    charge += 1.0 / (1.0 + 10 ** (ph - PKA_NTERM))
    # C-terminus (negative)
    charge -= 1.0 / (1.0 + 10 ** (PKA_CTERM - ph))

    for aa in seq:
        if aa in ("D", "E", "C", "Y"):
            pka = PKA_SIDE[aa]
            charge -= 1.0 / (1.0 + 10 ** (pka - ph))
        elif aa in ("H", "K", "R"):
            pka = PKA_SIDE[aa]
            charge += 1.0 / (1.0 + 10 ** (ph - pka))

    return charge


def _compute_pI(seq: str) -> float:
    """Binary search for isoelectric point."""
    lo, hi = 0.0, 14.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        charge = _net_charge_at_ph(seq, mid)
        if charge > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2.0, 2)


def _hydrophobic_patch_score(seq: str) -> float:
    """Fraction of residues that are strongly hydrophobic (KD > 2.0)."""
    if not seq:
        return 0.0
    hydro_count = sum(1 for aa in seq if HYDROPHOBICITY.get(aa, 0) > 2.0)
    return round(hydro_count / len(seq), 3)


def _beta_propensity_score(seq: str) -> float:
    """Mean β-sheet propensity (0–2 scale; >1.2 = elevated risk)."""
    if not seq:
        return 0.0
    total = sum(BETA_PROPENSITY.get(aa, 1.0) for aa in seq)
    return round(total / len(seq), 3)


def _self_dock_risk(structure: Structure, n_orientations: int = 4, seed: int = 42) -> float:
    """Dock the binder against a rotated copy of itself and return max interface score.

    This is a rough proxy for self-association tendency.  Higher values indicate
    the binder surface is "sticky" and may self-aggregate.
    """
    rng = np.random.default_rng(seed)
    max_score = 0.0

    for _ in range(n_orientations):
        partner = copy.deepcopy(structure)

        # Random rotation
        angles = rng.uniform(0, 2 * np.pi, size=3)
        cx, sx = np.cos(angles[0]), np.sin(angles[0])
        cy, sy = np.cos(angles[1]), np.sin(angles[1])
        cz, sz = np.cos(angles[2]), np.sin(angles[2])

        rot = np.array([
            [cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz],
            [cy * sz, sx * sy * sz + cx * cz, cx * sy * sz - sx * cz],
            [-sy, sx * cy, cx * cy],
        ])

        # Random translation (20–40 Å away to represent loose association)
        translation = rng.uniform(20.0, 40.0, size=3)

        model = partner[0]
        for chain in model:
            for residue in chain:
                for atom in residue:
                    xyz = atom.get_vector().get_array()
                    new_xyz = rot @ xyz + translation
                    atom.set_coord(new_xyz)

        ss = score_interface(structure, partner, contact_cutoff=10.0)
        max_score = max(max_score, ss.composite)

    return round(max_score, 3)


# ── Main function ────────────────────────────────────────────────────────────

def compute_developability(
    structure: Structure,
    seed: int = 42,
) -> DevelopabilityBreakdown:
    """Compute the full developability assessment for a binder structure.

    Returns a DevelopabilityBreakdown with individual scores and a composite
    score from 0 (worst) to 100 (best), plus a flag (PASS/WARN/FAIL).
    """
    seq = _extract_full_sequence(structure)

    hp = _hydrophobic_patch_score(seq)
    charge = round(_net_charge_at_ph(seq, 7.4), 2)
    pi = _compute_pI(seq)
    beta = _beta_propensity_score(seq)
    self_risk = _self_dock_risk(structure, n_orientations=4, seed=seed)

    # ── Composite scoring (100 = perfect) ────────────────────────────────
    penalties = 0.0

    # Hydrophobic patch: penalise if > 30% hydrophobic
    if hp > 0.30:
        penalties += (hp - 0.30) * 100  # up to ~20 points

    # Charge: ideal range –2 to +6 at pH 7.4
    if charge < -2 or charge > 8:
        penalties += min(abs(charge), 10) * 1.5

    # pI: ideal 6–9 for mAbs
    if pi < 5 or pi > 10:
        penalties += 10

    # Beta propensity: penalise if mean > 1.2
    if beta > 1.2:
        penalties += (beta - 1.2) * 30

    # Self-dock risk: penalise high self-association
    if self_risk > 3.0:
        penalties += (self_risk - 3.0) * 5

    composite = max(0.0, min(100.0, 100.0 - penalties))
    composite = round(composite, 1)

    # Flag
    if composite >= 70:
        flag = "PASS"
    elif composite >= 40:
        flag = "WARN"
    else:
        flag = "FAIL"

    return DevelopabilityBreakdown(
        hydrophobic_patch=hp,
        net_charge=charge,
        pI=pi,
        beta_propensity=beta,
        self_dock_risk=self_risk,
        composite=composite,
        flag=flag,
    )
