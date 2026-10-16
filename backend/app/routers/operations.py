"""Operational endpoints for live data refreshes."""

from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, BackgroundTasks, HTTPException

router = APIRouter(tags=["Operations"])
_refresh_lock = Lock()
_refresh_state = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "error": None,
}


def _run_refresh() -> None:
    """Run the complete data refresh outside the request thread."""
    with _refresh_lock:
        _refresh_state.update({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "error": None,
        })

    try:
        from app.data_pipeline.refresh import run_full_refresh
        from app.sentiment.aggregator import aggregate_sentiment

        run_full_refresh()
        aggregate_sentiment()
        _refresh_state["status"] = "completed"
    except Exception as error:
        _refresh_state.update({"status": "failed", "error": str(error)})
    finally:
        _refresh_state["finished_at"] = datetime.now(timezone.utc).isoformat()


@router.post("/refresh")
def start_refresh(background_tasks: BackgroundTasks):
    """Start a complete price, news, social, and sentiment refresh."""
    if _refresh_state["status"] == "running":
        raise HTTPException(status_code=409, detail="A refresh is already running")

    background_tasks.add_task(_run_refresh)
    return {"status": "started", "message": "Data refresh started in the background"}


@router.get("/refresh/status")
def get_refresh_status():
    """Return the current refresh job status."""
    return dict(_refresh_state)
