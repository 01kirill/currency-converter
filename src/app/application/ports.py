from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol, Self
from uuid import UUID

from app.application.dto import CurrencyReportRow
from app.domain.entities import Deal
from app.domain.value_objects import CurrencyCode, ExchangeRate


class Clock(Protocol):
    """Source of the current time"""

    def now(self) -> datetime:
        """Current aware datetime in Europe/Minsk"""
        ...


class RatesProvider(Protocol):
    """Source of official exchange rates"""

    async def fetch(self, on_date: date) -> list[ExchangeRate]:
        """Official NBRB rates for the date.
        Raises RatesNotAvailableError
        """
        ...


class RateRepository(Protocol):
    """Storage of daily exchange rates"""

    async def add_many(self, rates: Sequence[ExchangeRate]) -> None:
        """Save rates, skip already stored (currency, date) pairs"""
        ...

    async def exists(self, on_date: date) -> bool: ...

    async def get(self, code: CurrencyCode, on_date: date) -> ExchangeRate | None: ...


class DealRepository(Protocol):
    """Storage of exchange deals"""

    async def add(self, deal: Deal) -> None: ...

    async def get_for_update(self, deal_id: UUID) -> Deal | None:
        """Load deal and lock it until the transaction ends"""
        ...

    async def update(self, deal: Deal) -> None: ...

    async def list_pending(self) -> list[Deal]: ...

    async def report(
        self,
        date_from: date,
        date_to: date,
        currency: CurrencyCode | None,
    ) -> list[CurrencyReportRow]:
        """Totals of accepted deals resolved within [date_from, date_to], Minsk dates"""
        ...


class UnitOfWork(Protocol):
    """One transaction over both repositories, nothing is saved without commit()"""

    @property
    def deals(self) -> DealRepository: ...

    @property
    def rates(self) -> RateRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...
