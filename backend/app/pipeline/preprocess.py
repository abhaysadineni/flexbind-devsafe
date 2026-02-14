"""Step A — PDB preprocessing: cleaning, chain selection, renumbering, and interface detection."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional

import numpy as np
from Bio.PDB import PDBParser, PDBIO, Select
from Bio.PDB.Structure import Structure
from Bio.PDB.Model import Model
from Bio.PDB.Chain import Chain
from Bio.PDB.Residue import Residue

warnings.filterwarnings("ignore", category=Warning, module="Bio.PDB")

# Known antibody CDR residue ranges (Chothia numbering approximation).
ANTIBODY_CDR_RANGES: dict[str, list[tuple[int, int]]] = {
    "H": [(26, 32), (52, 56), (95, 102)],  # CDR-H1, H2, H3
    "L": [(24, 34), (50, 56), (89, 97)],    # CDR-L1, L2, L3
}


class CleanSelect(Select):
    """Keep only standard amino-acid ATOM records (no HETATM, water, etc.)."""

    STANDARD_AA = {
        "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
        "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL",
    }

    def accept_residue(self, residue: Residue) -> int:
        return 1 if residue.get_resname() in self.STANDARD_AA else 0

    def accept_atom(self, atom) -> int:
        return 1 if not atom.is_disordered() or atom.get_altloc() == "A" else 0


def clean_pdb(input_path: Path, output_path: Path) -> Structure:
    """Parse, clean, and write a sanitised PDB. Returns the cleaned structure."""
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("mol", str(input_path))

    io = PDBIO()
    io.set_structure(structure)
    io.save(str(output_path), CleanSelect())

    return parser.get_structure("clean", str(output_path))


def get_ca_coords(structure: Structure) -> dict[tuple[str, int], np.ndarray]:
    """Extract Cα coordinates as {(chain_id, resi): xyz}."""
    coords: dict[tuple[str, int], np.ndarray] = {}
    model: Model = structure[0]
    for chain in model:
        for residue in chain:
            if "CA" in residue:
                coords[(chain.id, residue.id[1])] = residue["CA"].get_vector().get_array()
    return coords


def detect_interface_residues(
    target_structure: Structure,
    binder_structure: Structure,
    cutoff_angstrom: float = 8.0,
) -> list[tuple[str, int]]:
    """Return binder residues within `cutoff_angstrom` of any target Cα."""
    target_ca = get_ca_coords(target_structure)
    binder_ca = get_ca_coords(binder_structure)

    if not target_ca or not binder_ca:
        raise ValueError("One or both structures have no Cα atoms after cleaning.")

    target_xyz = np.array(list(target_ca.values()))
    interface: list[tuple[str, int]] = []

    for key, bxyz in binder_ca.items():
        dists = np.linalg.norm(target_xyz - bxyz, axis=1)
        if dists.min() < cutoff_angstrom:
            interface.append(key)

    return interface


def detect_cdr_residues(
    binder_structure: Structure,
) -> list[tuple[str, int]]:
    """Identify CDR residues in an antibody Fv based on Chothia-like numbering."""
    model: Model = binder_structure[0]
    cdr_residues: list[tuple[str, int]] = []

    for chain in model:
        cid = chain.id.upper()
        ranges = ANTIBODY_CDR_RANGES.get(cid, [])
        if not ranges:
            # Try matching first chain to H, second to L
            continue
        for residue in chain:
            resi = residue.id[1]
            for start, end in ranges:
                if start <= resi <= end:
                    cdr_residues.append((chain.id, resi))
                    break
    return cdr_residues


def parse_flexible_residues(spec: str) -> list[tuple[str, int]]:
    """Parse a user string like 'A:30,A:31,B:52' into a residue list."""
    residues: list[tuple[str, int]] = []
    for token in spec.split(","):
        token = token.strip()
        if ":" in token:
            chain, resi = token.split(":", 1)
            residues.append((chain.strip(), int(resi.strip())))
    return residues


def get_flexible_residues(
    target_structure: Structure,
    binder_structure: Structure,
    binder_type: str,
    user_spec: Optional[str],
    cutoff: float = 8.0,
) -> list[tuple[str, int]]:
    """Determine which binder residues are flexible/designable."""
    if user_spec:
        return parse_flexible_residues(user_spec)
    if binder_type == "antibody_fv":
        cdr = detect_cdr_residues(binder_structure)
        if cdr:
            return cdr
    # Fall back to interface detection
    return detect_interface_residues(target_structure, binder_structure, cutoff)


def extract_sequence(structure: Structure) -> dict[str, str]:
    """Extract single-letter amino-acid sequences per chain."""
    from Bio.PDB.Polypeptide import three_to_one

    sequences: dict[str, str] = {}
    model: Model = structure[0]
    for chain in model:
        seq_chars: list[str] = []
        for residue in chain:
            try:
                seq_chars.append(three_to_one(residue.get_resname()))
            except KeyError:
                continue
        if seq_chars:
            sequences[chain.id] = "".join(seq_chars)
    return sequences
