from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo

from app.application.dto import CurrencyReportRow
from app.domain.entities import Deal
from app.domain.value_objects import CurrencyCode, DealStatus, ExchangeRate

MINSK = ZoneInfo("Europe/Minsk")
NOW = datetime(2026, 10, 19, 12, 0, tzinfo=MINSK)
TODAY = NOW.date()


def make_rate(code: str, rate: str, scale: int = 1, on_date: date = TODAY) -> ExchangeRate:
    return ExchangeRate(on_date, CurrencyCode(code), scale, Decimal(rate))


def make_deal(created_at: datetime = NOW) -> Deal:
    """A pending deal: 100 USD -> EUR"""
    usd = make_rate("USD", "3.0091", on_date=created_at.date())
    eur = make_rate("EUR", "3.3749", on_date=created_at.date())
    return Deal.create(Decimal(100), usd, eur, created_at)


class FixedClock:
    def __init__(self, at: datetime = NOW) -> None:
        self.at = at

    def now(self) -> datetime:
        return self.at


class FakeRatesProvider:
    def __init__(self, rates: list[ExchangeRate], error: Exception | None = None) -> None:
        self.rates = rates
        self.error = error
        self.calls: list[date] = []

    async def fetch(self, on_date: date) -> list[ExchangeRate]:
        self.calls.append(on_date)
        if self.error is not None:
            raise self.error
        return self.rates


class InMemoryRateRepository:
    def __init__(self, rates: Sequence[ExchangeRate] = ()) -> None:
        self.rates: dict[tuple[CurrencyCode, date], ExchangeRate] = {}
        for rate in rates:
            self.rates[(rate.currency_code, rate.rate_date)] = rate

    async def add_many(self, rates: Sequence[ExchangeRate]) -> None:
        for rate in rates:
            self.rates.setdefault((rate.currency_code, rate.rate_date), rate)

    async def exists(self, on_date: date) -> bool:
        return any(rate_date == on_date for _, rate_date in self.rates)

    async def get(self, code: CurrencyCode, on_date: date) -> ExchangeRate | None:
        return self.rates.get((code, on_date))


class InMemoryDealRepository:
    """Stores copies so a test fails if a use case forgets update()"""

    def __init__(self, deals: Sequence[Deal] = ()) -> None:
        self.deals = {deal.id: replace(deal) for deal in deals}
        self.report_rows: list[CurrencyReportRow] = []
        self.report_calls: list[tuple[date, date, CurrencyCode | None]] = []

    async def add(self, deal: Deal) -> None:
        self.deals[deal.id] = replace(deal)

    async def get_for_update(self, deal_id: UUID) -> Deal | None:
        deal = self.deals.get(deal_id)
        return replace(deal) if deal is not None else None

    async def update(self, deal: Deal) -> None:
        self.deals[deal.id] = replace(deal)

    async def list_pending(self) -> list[Deal]:
        return [replace(d) for d in self.deals.values() if d.status is DealStatus.PENDING]

    async def report(
        self, date_from: date, date_to: date, currency: CurrencyCode | None
    ) -> list[CurrencyReportRow]:
        self.report_calls.append((date_from, date_to, currency))
        return self.report_rows


class FakeUnitOfWork:
    def __init__(
        self,
        rates: InMemoryRateRepository | None = None,
        deals: InMemoryDealRepository | None = None,
    ) -> None:
        self.rates = rates or InMemoryRateRepository()
        self.deals = deals or InMemoryDealRepository()
        self.commits = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        pass

    async def commit(self) -> None:
        self.commits += 1
