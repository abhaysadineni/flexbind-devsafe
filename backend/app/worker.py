"""Background task runner using threads (no Celery/Redis needed)."""

import threading

def run_pipeline_task(job_id: str) -> None:
    """Run the pipeline in a background thread."""
    from app.pipeline.runner import run_pipeline

    def _run():
        try:
            run_pipeline(job_id)
        except Exception as e:
            print(f"Pipeline error for {job_id}: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
