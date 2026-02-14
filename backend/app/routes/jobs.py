"""Job management API endpoints."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app import config
from app.models import (
    BinderType,
    JobCreateParams,
    JobListItem,
    JobReport,
    JobStatus,
    JobStatusResponse,
    RunMode,
)
from app.utils import job_dir, new_job_id, read_meta, write_meta

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobStatusResponse, status_code=201)
async def create_job(
    target_pdb: UploadFile = File(..., description="Target/receptor PDB file"),
    binder_pdb: UploadFile = File(..., description="Binder template PDB file"),
    binder_type: str = Form("other"),
    flexible_residues: str = Form(""),
    interface_distance: float = Form(8.0),
    mode: str = Form("fast"),
    seed: int = Form(42),
    no_glycosylation: bool = Form(True),
) -> JobStatusResponse:
    """Create a new design job. Uploads PDB files and queues the pipeline."""

    # Validate file sizes
    for upload, label in [(target_pdb, "target"), (binder_pdb, "binder")]:
        if upload.size and upload.size > config.MAX_UPLOAD_BYTES:
            raise HTTPException(
                400, f"{label} PDB exceeds {config.MAX_UPLOAD_MB} MB limit"
            )
        if not upload.filename or not upload.filename.lower().endswith(".pdb"):
            raise HTTPException(400, f"{label} file must be a .pdb file")

    # Validate enums
    try:
        bt = BinderType(binder_type)
    except ValueError:
        raise HTTPException(400, f"Invalid binder_type: {binder_type}")
    try:
        rm = RunMode(mode)
    except ValueError:
        raise HTTPException(400, f"Invalid mode: {mode}")

    # Create job
    jid = new_job_id()
    jd = job_dir(jid)

    # Save uploaded files
    target_path = jd / "target.pdb"
    binder_path = jd / "binder.pdb"

    target_content = await target_pdb.read()
    binder_content = await binder_pdb.read()

    if len(target_content) < 50:
        raise HTTPException(400, "Target PDB file appears empty or too small")
    if len(binder_content) < 50:
        raise HTTPException(400, "Binder PDB file appears empty or too small")

    target_path.write_bytes(target_content)
    binder_path.write_bytes(binder_content)

    # Write metadata
    meta = {
        "job_id": jid,
        "status": JobStatus.QUEUED.value,
        "binder_type": bt.value,
        "mode": rm.value,
        "seed": seed,
        "flexible_residues": flexible_residues or None,
        "interface_distance": interface_distance,
        "no_glycosylation": no_glycosylation,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "progress": 0.0,
        "message": "Job queued",
    }
    write_meta(jid, meta)

    # Queue Celery task
    from app.worker import run_pipeline_task
    run_pipeline_task.delay(jid)

    return JobStatusResponse(
        job_id=jid, status=JobStatus.QUEUED, progress=0.0, message="Job queued"
    )


@router.get("", response_model=list[JobListItem])
async def list_jobs() -> list[JobListItem]:
    """List all jobs, newest first."""
    items: list[JobListItem] = []
    jobs_root = config.JOBS_DIR
    if not jobs_root.exists():
        return []

    for d in sorted(jobs_root.iterdir(), reverse=True):
        meta_path = d / "meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            items.append(JobListItem(
                job_id=meta["job_id"],
                status=JobStatus(meta.get("status", "queued")),
                binder_type=BinderType(meta.get("binder_type", "other")),
                mode=RunMode(meta.get("mode", "fast")),
                created_at=meta.get("created_at", ""),
                progress=meta.get("progress", 0.0),
            ))

    return items[:50]  # Cap at 50 most recent


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get current status of a job."""
    try:
        meta = read_meta(job_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=meta["job_id"],
        status=JobStatus(meta.get("status", "queued")),
        progress=meta.get("progress", 0.0),
        message=meta.get("message", ""),
    )


@router.get("/{job_id}/report", response_model=JobReport)
async def get_job_report(job_id: str) -> JobReport:
    """Get the full report for a completed job."""
    jd = job_dir(job_id)
    report_path = jd / "report.json"
    if not report_path.exists():
        raise HTTPException(404, "Report not ready or job not found")

    with open(report_path) as f:
        return JobReport(**json.load(f))


@router.get("/{job_id}/logs")
async def stream_logs(job_id: str):
    """Server-Sent Events stream of job logs."""
    jd = job_dir(job_id)
    log_path = jd / "log.txt"

    async def event_generator():
        last_pos = 0
        while True:
            try:
                meta = read_meta(job_id)
            except FileNotFoundError:
                yield f"data: Job not found\n\n"
                return

            status = meta.get("status", "queued")

            if log_path.exists():
                with open(log_path) as f:
                    f.seek(last_pos)
                    new_lines = f.read()
                    new_pos = f.tell()

                if new_lines:
                    last_pos = new_pos
                    for line in new_lines.strip().split("\n"):
                        if line:
                            yield f"data: {json.dumps({'log': line, 'status': status, 'progress': meta.get('progress', 0)})}\n\n"

            if status in ("done", "failed"):
                yield f"data: {json.dumps({'log': f'Job {status}', 'status': status, 'progress': meta.get('progress', 1.0)})}\n\n"
                return

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/download")
async def download_results(job_id: str):
    """Download the results ZIP for a completed job."""
    jd = job_dir(job_id)
    zip_path = jd / "results.zip"
    if not zip_path.exists():
        raise HTTPException(404, "Results ZIP not ready")

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"flexbind-{job_id}.zip",
    )
