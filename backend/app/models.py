"""Pydantic models for API requests, responses, and internal data structures."""

from __future__ import annotations

import enum
from typing import Optional

from pydantic import BaseModel, Field


class BinderType(str, enum.Enum):
    ANTIBODY_FV = "antibody_fv"
    OTHER = "other"


class RunMode(str, enum.Enum):
    FAST = "fast"
    DEEP = "deep"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# ── Request models ──────────────────────────────────────────────────────────


class JobCreateParams(BaseModel):
    """Metadata submitted alongside uploaded PDB files."""

    binder_type: BinderType = BinderType.OTHER
    flexible_residues: Optional[str] = Field(
        None,
        description="Comma-separated residue IDs (e.g. 'A:30,A:31,A:52') or empty for auto-detect.",
    )
    interface_distance: float = Field(
        8.0, ge=3.0, le=20.0, description="Auto-detect interface cutoff in Angstroms."
    )
    mode: RunMode = RunMode.FAST
    seed: int = Field(42, ge=0, le=2**31 - 1)
    no_glycosylation: bool = Field(True, description="Forbid N-X-S/T motifs in designed sequences.")


# ── Internal pipeline data ──────────────────────────────────────────────────


class ResidueScore(BaseModel):
    chain: str
    resi: int
    resn: str
    score: float


class StateScore(BaseModel):
    state_index: int
    contact_score: float
    clash_score: float
    hbond_proxy: float
    sasa_burial: float
    composite: float


class DesignResult(BaseModel):
    rank: int
    sequence: str
    mutations: str
    mean_score: float
    worst_score: float
    robustness: float
    developability_score: float
    developability_flag: str
    per_state_scores: list[StateScore]


class DevelopabilityBreakdown(BaseModel):
    hydrophobic_patch: float
    net_charge: float
    pI: float
    beta_propensity: float
    self_dock_risk: float
    composite: float
    flag: str


class JobReport(BaseModel):
    job_id: str
    status: JobStatus
    binder_type: BinderType
    mode: RunMode
    seed: int
    ensemble_size: int = 0
    designs: list[DesignResult] = []
    developability: Optional[DevelopabilityBreakdown] = None
    errors: list[str] = []


# ── Response models ─────────────────────────────────────────────────────────


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = 0.0
    message: str = ""


class JobListItem(BaseModel):
    job_id: str
    status: JobStatus
    binder_type: BinderType
    mode: RunMode
    created_at: str
    progress: float = 0.0


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
