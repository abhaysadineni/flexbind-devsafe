"""Pytest fixtures — including tiny synthetic PDB structures for pipeline smoke tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from Bio.PDB import PDBParser
from Bio.PDB.Structure import Structure


# Minimal PDB content: a 5-residue alpha-helix (chain A) as "target"
MINI_TARGET_PDB = textwrap.dedent("""\
    ATOM      1  N   ALA A   1       1.000   1.000   1.000  1.00  0.00           N
    ATOM      2  CA  ALA A   1       2.000   1.000   1.000  1.00  0.00           C
    ATOM      3  C   ALA A   1       3.000   1.000   1.000  1.00  0.00           C
    ATOM      4  O   ALA A   1       3.500   2.000   1.000  1.00  0.00           O
    ATOM      5  CB  ALA A   1       2.000   0.000   0.000  1.00  0.00           C
    ATOM      6  N   GLY A   2       3.500   0.000   1.000  1.00  0.00           N
    ATOM      7  CA  GLY A   2       4.500   0.000   1.000  1.00  0.00           C
    ATOM      8  C   GLY A   2       5.500   0.000   1.000  1.00  0.00           C
    ATOM      9  O   GLY A   2       6.000   1.000   1.000  1.00  0.00           O
    ATOM     10  N   LEU A   3       6.000  -1.000   1.000  1.00  0.00           N
    ATOM     11  CA  LEU A   3       7.000  -1.000   1.000  1.00  0.00           C
    ATOM     12  C   LEU A   3       8.000  -1.000   1.000  1.00  0.00           C
    ATOM     13  O   LEU A   3       8.500   0.000   1.000  1.00  0.00           O
    ATOM     14  CB  LEU A   3       7.000  -2.000   0.000  1.00  0.00           C
    ATOM     15  N   SER A   4       8.500  -2.000   1.000  1.00  0.00           N
    ATOM     16  CA  SER A   4       9.500  -2.000   1.000  1.00  0.00           C
    ATOM     17  C   SER A   4      10.500  -2.000   1.000  1.00  0.00           C
    ATOM     18  O   SER A   4      11.000  -1.000   1.000  1.00  0.00           O
    ATOM     19  CB  SER A   4       9.500  -3.000   0.000  1.00  0.00           C
    ATOM     20  N   VAL A   5      11.000  -3.000   1.000  1.00  0.00           N
    ATOM     21  CA  VAL A   5      12.000  -3.000   1.000  1.00  0.00           C
    ATOM     22  C   VAL A   5      13.000  -3.000   1.000  1.00  0.00           C
    ATOM     23  O   VAL A   5      13.500  -2.000   1.000  1.00  0.00           O
    ATOM     24  CB  VAL A   5      12.000  -4.000   0.000  1.00  0.00           C
    END
""")

# Minimal binder: a 5-residue strand (chain B) placed near target
MINI_BINDER_PDB = textwrap.dedent("""\
    ATOM      1  N   LYS B   1       3.000   4.000   1.000  1.00  0.00           N
    ATOM      2  CA  LYS B   1       4.000   4.000   1.000  1.00  0.00           C
    ATOM      3  C   LYS B   1       5.000   4.000   1.000  1.00  0.00           C
    ATOM      4  O   LYS B   1       5.500   5.000   1.000  1.00  0.00           O
    ATOM      5  CB  LYS B   1       4.000   3.000   0.000  1.00  0.00           C
    ATOM      6  N   ASP B   2       5.500   3.000   1.000  1.00  0.00           N
    ATOM      7  CA  ASP B   2       6.500   3.000   1.000  1.00  0.00           C
    ATOM      8  C   ASP B   2       7.500   3.000   1.000  1.00  0.00           C
    ATOM      9  O   ASP B   2       8.000   4.000   1.000  1.00  0.00           O
    ATOM     10  CB  ASP B   2       6.500   2.000   0.000  1.00  0.00           C
    ATOM     11  N   PHE B   3       8.000   2.000   1.000  1.00  0.00           N
    ATOM     12  CA  PHE B   3       9.000   2.000   1.000  1.00  0.00           C
    ATOM     13  C   PHE B   3      10.000   2.000   1.000  1.00  0.00           C
    ATOM     14  O   PHE B   3      10.500   3.000   1.000  1.00  0.00           O
    ATOM     15  CB  PHE B   3       9.000   1.000   0.000  1.00  0.00           C
    ATOM     16  N   GLN B   4      10.500   1.000   1.000  1.00  0.00           N
    ATOM     17  CA  GLN B   4      11.500   1.000   1.000  1.00  0.00           C
    ATOM     18  C   GLN B   4      12.500   1.000   1.000  1.00  0.00           C
    ATOM     19  O   GLN B   4      13.000   2.000   1.000  1.00  0.00           O
    ATOM     20  CB  GLN B   4      11.500   0.000   0.000  1.00  0.00           C
    ATOM     21  N   ALA B   5      13.000   0.000   1.000  1.00  0.00           N
    ATOM     22  CA  ALA B   5      14.000   0.000   1.000  1.00  0.00           C
    ATOM     23  C   ALA B   5      15.000   0.000   1.000  1.00  0.00           C
    ATOM     24  O   ALA B   5      15.500   1.000   1.000  1.00  0.00           O
    ATOM     25  CB  ALA B   5      14.000  -1.000   0.000  1.00  0.00           C
    END
""")


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def target_pdb_path(tmp_dir: Path) -> Path:
    p = tmp_dir / "target.pdb"
    p.write_text(MINI_TARGET_PDB)
    return p


@pytest.fixture
def binder_pdb_path(tmp_dir: Path) -> Path:
    p = tmp_dir / "binder.pdb"
    p.write_text(MINI_BINDER_PDB)
    return p


@pytest.fixture
def target_structure(target_pdb_path: Path) -> Structure:
    return PDBParser(QUIET=True).get_structure("target", str(target_pdb_path))


@pytest.fixture
def binder_structure(binder_pdb_path: Path) -> Structure:
    return PDBParser(QUIET=True).get_structure("binder", str(binder_pdb_path))
