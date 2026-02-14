"""Shared utility functions for the FlexBind pipeline."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import JOBS_DIR
from app.models import JobStatus


def new_job_id() -> str:
    """Generate a compact job identifier."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


def job_dir(job_id: str) -> Path:
    """Return (and ensure existence of) the job working directory."""
    d = JOBS_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_meta(job_id: str) -> dict[str, Any]:
    """Read the job metadata JSON from disk."""
    meta_path = job_dir(job_id) / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Job {job_id} not found")
    with open(meta_path) as f:
        return json.load(f)


def write_meta(job_id: str, data: dict[str, Any]) -> None:
    """Atomically write job metadata to disk."""
    meta_path = job_dir(job_id) / "meta.json"
    tmp = meta_path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.replace(meta_path)


def update_meta(job_id: str, **kwargs: Any) -> dict[str, Any]:
    """Read-modify-write helper for job metadata."""
    meta = read_meta(job_id)
    meta.update(kwargs)
    write_meta(job_id, meta)
    return meta


def append_log(job_id: str, message: str) -> None:
    """Append a timestamped line to the job log file."""
    log_path = job_dir(job_id) / "log.txt"
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"[{ts}] {message}\n")


def set_progress(job_id: str, progress: float, message: str = "") -> None:
    """Update progress (0.0–1.0) in metadata and log the message."""
    update_meta(job_id, progress=round(progress, 3), message=message)
    if message:
        append_log(job_id, message)


def set_status(job_id: str, status: JobStatus, message: str = "") -> None:
    """Update job status in metadata."""
    update_meta(job_id, status=status.value, message=message)
    append_log(job_id, f"STATUS → {status.value}" + (f": {message}" if message else ""))
