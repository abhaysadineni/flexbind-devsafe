"""Tests for the preprocessing module."""

from app.pipeline.preprocess import (
    clean_pdb,
    detect_interface_residues,
    extract_sequence,
    get_ca_coords,
    parse_flexible_residues,
)


def test_clean_pdb_produces_valid_output(target_pdb_path, tmp_dir):
    out = tmp_dir / "clean.pdb"
    struct = clean_pdb(target_pdb_path, out)
    assert out.exists()
    coords = get_ca_coords(struct)
    assert len(coords) == 5  # 5 residues in mini target


def test_get_ca_coords(target_structure):
    coords = get_ca_coords(target_structure)
    assert len(coords) == 5
    assert ("A", 1) in coords
    assert ("A", 5) in coords


def test_detect_interface_residues(target_structure, binder_structure):
    interface = detect_interface_residues(target_structure, binder_structure, cutoff_angstrom=10.0)
    # With a generous cutoff, several binder residues should be within range
    assert len(interface) > 0
    # All should be chain B
    for chain, resi in interface:
        assert chain == "B"


def test_parse_flexible_residues():
    result = parse_flexible_residues("A:30, A:31, B:52")
    assert result == [("A", 30), ("A", 31), ("B", 52)]


def test_parse_flexible_residues_empty():
    assert parse_flexible_residues("") == []


def test_extract_sequence(target_structure):
    seqs = extract_sequence(target_structure)
    assert "A" in seqs
    assert seqs["A"] == "AGLSV"
