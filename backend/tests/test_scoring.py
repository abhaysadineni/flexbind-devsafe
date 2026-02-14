"""Tests for scoring and developability modules."""

from app.pipeline.scoring import score_interface, score_ensemble
from app.pipeline.developability import (
    _compute_pI,
    _hydrophobic_patch_score,
    _net_charge_at_ph,
    compute_developability,
)
from app.pipeline.ensemble import generate_ensemble


def test_score_interface_nonzero(target_structure, binder_structure):
    ss = score_interface(target_structure, binder_structure)
    assert ss.composite > 0
    assert ss.contact_score >= 0
    assert ss.clash_score >= 0


def test_score_interface_deterministic(target_structure, binder_structure):
    s1 = score_interface(target_structure, binder_structure)
    s2 = score_interface(target_structure, binder_structure)
    assert s1.composite == s2.composite


def test_score_ensemble_returns_per_state(target_structure, binder_structure):
    flex = [("B", 1), ("B", 2), ("B", 3)]
    ensemble = generate_ensemble(
        binder_structure, target_structure, flex,
        n_samples=4, n_clusters=2, seed=42,
    )
    scores = score_ensemble(target_structure, ensemble)
    assert len(scores) == len(ensemble)
    for i, s in enumerate(scores):
        assert s.state_index == i


def test_hydrophobic_patch_score():
    # All hydrophobic
    assert _hydrophobic_patch_score("IVLFC") > 0.5
    # All polar
    assert _hydrophobic_patch_score("DENKR") == 0.0


def test_net_charge():
    # Pure lysines should be positive at pH 7.4
    charge = _net_charge_at_ph("KKKK", 7.4)
    assert charge > 2.0
    # Pure aspartates should be negative
    charge = _net_charge_at_ph("DDDD", 7.4)
    assert charge < -2.0


def test_compute_pI():
    pi = _compute_pI("KKKKKDDDDD")
    assert 4.0 < pi < 10.0


def test_developability_returns_score(binder_structure):
    dev = compute_developability(binder_structure, seed=42)
    assert 0 <= dev.composite <= 100
    assert dev.flag in ("PASS", "WARN", "FAIL")
    assert dev.pI > 0
