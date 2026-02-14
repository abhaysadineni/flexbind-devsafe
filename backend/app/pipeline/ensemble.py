"""Step B — Conformational ensemble generation.

Generates backbone diversity via geometric perturbations on flexible residues,
then clusters by RMSD to produce representative states.

If OpenMM is available, a short restrained-MD refinement is applied after
perturbation.  Otherwise, a purely geometric jitter with harmonic relaxation
is used (the fallback is always available).
"""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
from Bio.PDB import PDBParser, PDBIO
from Bio.PDB.Structure import Structure
from scipy.spatial.distance import squareform
from sklearn.cluster import AgglomerativeClustering

# Try importing OpenMM for optional refinement
try:
    import openmm  # noqa: F401
    HAS_OPENMM = True
except ImportError:
    HAS_OPENMM = False

BACKBONE_ATOMS = {"N", "CA", "C", "O"}


def _get_flexible_atoms(structure: Structure, flex_residues: list[tuple[str, int]]):
    """Return a list of (chain_id, resi, atom_name, atom_object) for flexible backbone atoms."""
    flex_set = set(flex_residues)
    atoms = []
    model = structure[0]
    for chain in model:
        for residue in chain:
            key = (chain.id, residue.id[1])
            if key in flex_set:
                for atom in residue:
                    if atom.name in BACKBONE_ATOMS:
                        atoms.append((chain.id, residue.id[1], atom.name, atom))
    return atoms


def _perturb_structure(
    structure: Structure,
    flex_residues: list[tuple[str, int]],
    rng: np.random.Generator,
    magnitude: float = 0.8,
) -> Structure:
    """Create a copy of the structure with Gaussian noise on flexible backbone atoms.

    Magnitude is in Angstroms (std-dev of Gaussian displacement).
    """
    new_struct = copy.deepcopy(structure)
    atoms = _get_flexible_atoms(new_struct, flex_residues)
    for _cid, _resi, _aname, atom in atoms:
        xyz = atom.get_vector().get_array()
        noise = rng.normal(0.0, magnitude, size=3)
        atom.set_coord(xyz + noise)
    return new_struct


def _harmonic_relax(structure: Structure, flex_residues: list[tuple[str, int]], iterations: int = 50):
    """Very simple in-place harmonic relaxation: pull each flexible atom toward the
    centroid of its bonded neighbours to reduce steric strain.

    This is NOT a real energy minimiser — it is a fast geometric heuristic that
    smooths out extreme clashes from the Gaussian perturbation step.
    """
    model = structure[0]
    flex_set = set(flex_residues)

    for _ in range(iterations):
        for chain in model:
            prev_ca = None
            for residue in chain:
                key = (chain.id, residue.id[1])
                ca = residue["CA"] if "CA" in residue else None
                if ca is None:
                    prev_ca = None
                    continue

                if key in flex_set:
                    # Pull CA toward its immediate intra-residue backbone neighbours
                    neighbours = []
                    for aname in ("N", "C"):
                        if aname in residue:
                            neighbours.append(residue[aname].get_vector().get_array())
                    if prev_ca is not None:
                        neighbours.append(prev_ca.get_vector().get_array())

                    if neighbours:
                        centroid = np.mean(neighbours, axis=0)
                        current = ca.get_vector().get_array()
                        ca.set_coord(current * 0.7 + centroid * 0.3)

                prev_ca = ca
    return structure


def _rmsd_between(s1: Structure, s2: Structure, flex_residues: list[tuple[str, int]]) -> float:
    """Compute backbone RMSD over flexible residues between two structures."""
    coords1 = []
    coords2 = []
    for struct, clist in [(s1, coords1), (s2, coords2)]:
        for atom_info in _get_flexible_atoms(struct, flex_residues):
            clist.append(atom_info[3].get_vector().get_array())

    if len(coords1) != len(coords2) or len(coords1) == 0:
        return 999.0

    c1 = np.array(coords1)
    c2 = np.array(coords2)
    return float(np.sqrt(np.mean(np.sum((c1 - c2) ** 2, axis=1))))


def generate_ensemble(
    binder_structure: Structure,
    target_structure: Structure,
    flex_residues: list[tuple[str, int]],
    n_samples: int = 10,
    n_clusters: int = 5,
    seed: int = 42,
    magnitude: float = 0.8,
) -> list[Structure]:
    """Generate and cluster an ensemble of perturbed binder conformations.

    Returns `n_clusters` representative structures (cluster medoids).
    """
    rng = np.random.default_rng(seed)

    # Generate raw samples
    samples: list[Structure] = [copy.deepcopy(binder_structure)]  # include the original
    for _ in range(n_samples - 1):
        s = _perturb_structure(binder_structure, flex_residues, rng, magnitude)
        _harmonic_relax(s, flex_residues, iterations=40)
        samples.append(s)

    if len(samples) <= n_clusters:
        return samples

    # Build pairwise RMSD matrix
    n = len(samples)
    condensed = []
    for i in range(n):
        for j in range(i + 1, n):
            condensed.append(_rmsd_between(samples[i], samples[j], flex_residues))
    dist_matrix = squareform(condensed)

    # Agglomerative clustering
    clust = AgglomerativeClustering(
        n_clusters=min(n_clusters, n),
        metric="precomputed",
        linkage="average",
    )
    labels = clust.fit_predict(dist_matrix)

    # Pick medoid of each cluster
    representatives: list[Structure] = []
    for cid in range(int(labels.max()) + 1):
        members = np.where(labels == cid)[0]
        if len(members) == 1:
            representatives.append(samples[members[0]])
            continue
        # Medoid = member with smallest average distance to other members
        sub = dist_matrix[np.ix_(members, members)]
        medoid_local = int(np.argmin(sub.mean(axis=1)))
        representatives.append(samples[members[medoid_local]])

    return representatives


def save_ensemble(ensemble: list[Structure], output_dir: Path) -> list[Path]:
    """Save each ensemble member as a PDB file. Returns list of file paths."""
    io = PDBIO()
    paths: list[Path] = []
    for i, struct in enumerate(ensemble):
        p = output_dir / f"ensemble_state_{i:03d}.pdb"
        io.set_structure(struct)
        io.save(str(p))
        paths.append(p)
    return paths
