from datetime import date
from decimal import Decimal

import pytest

from app.application.dto import CurrencyReportRow, DealReportQuery
from app.application.use_cases.get_deals_report import GetDealsReport
from app.domain.exceptions import CurrencyCodeError, InvalidPeriodError
from app.domain.value_objects import CurrencyCode
from tests.fakes import FakeUnitOfWork

DATE_FROM = date(2026, 10, 1)
DATE_TO = date(2026, 10, 19)
USD_ROW = CurrencyReportRow(CurrencyCode("USD"), Decimal("100.00"), Decimal("0.00"), 1)


async def test_returns_rows_from_repository_for_currency() -> None:
    uow = FakeUnitOfWork()
    uow.deals.report_rows = [USD_ROW]
    report = GetDealsReport(uow)

    rows = await report(DealReportQuery(DATE_FROM, DATE_TO, "USD"))

    assert rows == [USD_ROW]
    assert uow.deals.report_calls == [(DATE_FROM, DATE_TO, CurrencyCode("USD"))]
    assert uow.commits == 0


async def test_without_currency_passes_none() -> None:
    uow = FakeUnitOfWork()
    report = GetDealsReport(uow)

    await report(DealReportQuery(DATE_FROM, DATE_TO))

    assert uow.deals.report_calls == [(DATE_FROM, DATE_TO, None)]


async def test_single_day_period_is_allowed() -> None:
    uow = FakeUnitOfWork()
    report = GetDealsReport(uow)

    await report(DealReportQuery(DATE_TO, DATE_TO))

    assert uow.deals.report_calls == [(DATE_TO, DATE_TO, None)]


async def test_inverted_period_raises_and_skips_repository() -> None:
    uow = FakeUnitOfWork()
    report = GetDealsReport(uow)

    with pytest.raises(InvalidPeriodError):
        await report(DealReportQuery(DATE_TO, DATE_FROM))

    assert uow.deals.report_calls == []


async def test_invalid_currency_raises_currency_code_error() -> None:
    uow = FakeUnitOfWork()
    report = GetDealsReport(uow)

    with pytest.raises(CurrencyCodeError):
        await report(DealReportQuery(DATE_FROM, DATE_TO, "usd"))

    assert uow.deals.report_calls == []
