import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, time, timedelta

from app.application.ports import Clock

logger = logging.getLogger(__name__)

AFTER_MIDNIGHT = timedelta(minutes=5)


def seconds_until_next_day(now: datetime) -> float:
    """Seconds from now to a few minutes past next midnight in now's timezone"""
    next_midnight = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=now.tzinfo)
    return (next_midnight + AFTER_MIDNIGHT - now).total_seconds()


async def run_daily_rates(
    load_rates: Callable[[], Awaitable[int]],
    clock: Clock,
    retry_seconds: float,
) -> None:
    """Load today's rates now and after every midnight, retry on failure. Runs until cancelled"""
    while True:
        try:
            count = await load_rates()
        except Exception:
            logger.exception("Loading rates failed, retry in %s s", retry_seconds)
            delay = retry_seconds
        else:
            logger.info("Rates loaded: %s new", count)
            delay = seconds_until_next_day(clock.now())
        await asyncio.sleep(delay)
