from datetime import datetime
from zoneinfo import ZoneInfo

MINSK = ZoneInfo("Europe/Minsk")


class MinskClock:
    """Current time at Europe/Minsk, timezone of NBRB rates and reports"""

    def now(self) -> datetime:
        return datetime.now(MINSK)
