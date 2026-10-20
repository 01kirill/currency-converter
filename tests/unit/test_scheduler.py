from datetime import datetime

from app.infrastructure.clock import MINSK
from app.infrastructure.scheduler import seconds_until_next_day


def test_wakes_up_five_minutes_after_next_midnight() -> None:
    assert seconds_until_next_day(datetime(2026, 10, 20, 23, 0, tzinfo=MINSK)) == 65 * 60


def test_just_after_midnight_waits_almost_a_day() -> None:
    assert seconds_until_next_day(datetime(2026, 10, 20, 0, 1, tzinfo=MINSK)) == 24 * 3600 + 4 * 60
