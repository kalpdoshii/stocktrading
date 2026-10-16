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


def _scheduler_loop() -> None:
    logger.info(
        "Auto refresh enabled: weekdays at %02d:%02d %s",
        AUTO_REFRESH_HOUR,
        AUTO_REFRESH_MINUTE,
        AUTO_REFRESH_TIMEZONE,
    )
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
