"""Application configuration loaded from environment variables."""

import os
from pathlib import Path


CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

JOBS_DIR: Path = Path(os.getenv("JOBS_DIR", "./jobs"))
JOBS_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024

CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

DEFAULT_SEED: int = int(os.getenv("DEFAULT_SEED", "42"))

# Pipeline defaults
FAST_ENSEMBLE_SIZE: int = 5
DEEP_ENSEMBLE_SIZE: int = 20
FAST_DESIGN_CANDIDATES: int = 8
DEEP_DESIGN_CANDIDATES: int = 50
TOP_K_RESULTS: int = 10
INTERFACE_DISTANCE_CUTOFF: float = 8.0  # Angstroms
