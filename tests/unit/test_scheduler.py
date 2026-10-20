import asyncio
from datetime import datetime

import pytest

from app.domain.exceptions import RatesNotAvailableError
from app.infrastructure.clock import MINSK
from app.infrastructure.scheduler import run_daily_rates, seconds_until_next_day
from tests.fakes import TODAY, FixedClock


def test_wakes_up_five_minutes_after_next_midnight() -> None:
    assert seconds_until_next_day(datetime(2026, 10, 20, 23, 0, tzinfo=MINSK)) == 65 * 60


def test_just_after_midnight_waits_almost_a_day() -> None:
    assert seconds_until_next_day(datetime(2026, 10, 20, 0, 1, tzinfo=MINSK)) == 24 * 3600 + 4 * 60


async def test_retries_after_failure_then_sleeps_until_next_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results: list[int | Exception] = [RatesNotAvailableError(TODAY), 31]

    async def load_rates() -> int:
        result = results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)
        if not results:
            raise asyncio.CancelledError  # stop the endless loop after the second attempt

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await run_daily_rates(load_rates, FixedClock(), retry_seconds=600)

    assert delays == [600, 12 * 3600 + 5 * 60]  # FixedClock is 12:00 in Minsk
