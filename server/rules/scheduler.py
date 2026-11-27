"""
Background Periodic Scheduler for Automatic Government Rule Synchronization.
Runs inside FastAPI application lifespan (no external broker required) with clean shutdown.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from server.config.settings import get_settings
from server.logging.logger import get_logger
from server.rules.sync_service import GovernmentRuleSyncService

logger = get_logger("server.rules.scheduler")


class GovernmentRuleScheduler:
    """Async periodic background worker triggering GovernmentRuleSyncService."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        self.next_run_iso: str | None = None

    def start(self) -> None:
        settings = get_settings()
        if not settings.RULE_SYNC_ENABLED:
            logger.info("Automatic government rule sync scheduler is disabled via RULE_SYNC_ENABLED=false.")
            return
        if self._task and not self._task.done():
            return

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="gov-rule-sync-scheduler")
        logger.info(
            "Government rule sync scheduler started (interval=%.2fh, initial_delay=%.1fs).",
            settings.RULE_SYNC_INTERVAL_HOURS,
            settings.RULE_SYNC_INITIAL_DELAY_SECONDS,
        )

    async def stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.next_run_iso = None
        logger.info("Government rule sync scheduler stopped cleanly.")

    async def _sleep_interruptible(self, seconds: float) -> bool:
        """Waits `seconds` or returns True immediately if shutdown was requested."""
        assert self._stop_event is not None
        self.next_run_iso = (datetime.now(timezone.utc) + timedelta(seconds=max(0.0, seconds))).isoformat()
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=max(0.1, seconds))
            return True
        except asyncio.TimeoutError:
            return False

    async def _run_loop(self) -> None:
        settings = get_settings()
        interval_seconds = max(60.0, settings.RULE_SYNC_INTERVAL_HOURS * 3600.0)
        initial_delay = max(1.0, settings.RULE_SYNC_INITIAL_DELAY_SECONDS)

        if await self._sleep_interruptible(initial_delay):
            return

        service = GovernmentRuleSyncService()
        while True:
            try:
                report = await asyncio.to_thread(service.sync_now, "scheduled")
                logger.info(
                    "Scheduled government rule sync finished: status=%s new=%d updated=%d manual_review=%d",
                    report.overall_status,
                    report.new_rules_detected,
                    report.updated_rules,
                    report.manual_review_rules,
                )
            except Exception as exc:
                logger.error("Scheduled government rule sync crashed cleanly without stopping loop: %s", exc)

            if await self._sleep_interruptible(interval_seconds):
                return


_scheduler_instance = GovernmentRuleScheduler()


def get_rule_scheduler() -> GovernmentRuleScheduler:
    return _scheduler_instance
