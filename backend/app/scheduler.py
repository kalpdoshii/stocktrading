"""Simple weekday scheduler for the Indian market refresh."""

import logging
from datetime import datetime, timedelta
from threading import Event, Thread
from zoneinfo import ZoneInfo

from app.config import (
    AUTO_REFRESH_ENABLED,
    AUTO_REFRESH_HOUR,
    AUTO_REFRESH_MINUTE,
    AUTO_REFRESH_TIMEZONE,
)
from app.routers.operations import _run_refresh, _refresh_state

logger = logging.getLogger(__name__)
_stop_event = Event()
_scheduler_thread = None


def _seconds_until_next_run() -> float:
    timezone = ZoneInfo(AUTO_REFRESH_TIMEZONE)
    now = datetime.now(timezone)
    target = now.replace(
        hour=AUTO_REFRESH_HOUR,
        minute=AUTO_REFRESH_MINUTE,
        second=0,
        microsecond=0,
    )
    if target <= now or now.weekday() >= 5:
        target += timedelta(days=1)
    while target.weekday() >= 5:
        target += timedelta(days=1)
    return max(1.0, (target - now).total_seconds())


def _check_and_run_initial_refresh() -> None:
    """Check on startup if market has closed today and today's price data is missing."""
    try:
        from app.database import SessionLocal
        from app.models import PriceData
        from sqlalchemy import func

        db = SessionLocal()
        latest = db.query(func.max(PriceData.date)).scalar()
        db.close()

        timezone = ZoneInfo(AUTO_REFRESH_TIMEZONE)
        now = datetime.now(timezone)
        today = now.date()

        # If today is a weekday, market has closed (>= 16:00 IST), and today's data is missing:
        if now.weekday() < 5 and now.hour >= AUTO_REFRESH_HOUR and (not latest or latest < today):
            logger.info(
                "Catch-up refresh triggered: latest stored date is %s, today is %s",
                latest,
                today,
            )
            _run_refresh()
    except Exception as e:
        logger.warning("Startup refresh check warning: %s", e)


def _scheduler_loop() -> None:
    logger.info(
        "Auto refresh enabled: weekdays at %02d:%02d %s",
        AUTO_REFRESH_HOUR,
        AUTO_REFRESH_MINUTE,
        AUTO_REFRESH_TIMEZONE,
    )
    # Check if a catch-up run is needed immediately upon startup
    _check_and_run_initial_refresh()

    while not _stop_event.wait(_seconds_until_next_run()):
        if _refresh_state["status"] != "running":
            logger.info("Starting scheduled Indian market refresh")
            _run_refresh()


def start_scheduler() -> None:
    global _scheduler_thread
    if not AUTO_REFRESH_ENABLED or (_scheduler_thread and _scheduler_thread.is_alive()):
        return
    _stop_event.clear()
    _scheduler_thread = Thread(target=_scheduler_loop, name="market-refresh-scheduler", daemon=True)
    _scheduler_thread.start()


def stop_scheduler() -> None:
    _stop_event.set()
