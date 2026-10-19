from datetime import timedelta
from decimal import Decimal

import pytest

from app.application.dto import CreateDealCommand
from app.application.use_cases.create_deal import CreateDeal
from app.domain.exceptions import (
    CurrencyCodeError,
    RatesNotAvailableError,
    SameCurrencyExchangeError,
    UnsupportedCurrencyError,
)
from app.domain.value_objects import BYN, CurrencyCode, DealStatus
from tests.fakes import NOW, TODAY, FakeUnitOfWork, FixedClock, InMemoryRateRepository, make_rate

USD = make_rate("USD", "3.0091")
EUR = make_rate("EUR", "3.3749")


def make_uow() -> FakeUnitOfWork:
    """Rates for USD and EUR are loaded for today"""
    return FakeUnitOfWork(rates=InMemoryRateRepository([USD, EUR]))


async def test_creates_pending_deal_and_saves_it() -> None:
    uow = make_uow()
    create = CreateDeal(uow, FixedClock())

    deal = await create(CreateDealCommand(Decimal(100), "USD", "EUR"))

    assert deal.status is DealStatus.PENDING
    assert deal.from_currency == CurrencyCode("USD")
    assert deal.to_currency == CurrencyCode("EUR")
    assert deal.converted_amount == Decimal("89.16")
    assert deal.created_at == NOW
    assert uow.deals.deals[deal.id].status is DealStatus.PENDING
    assert uow.commits == 1


async def test_reverse_direction_gives_other_amount() -> None:
    create = CreateDeal(make_uow(), FixedClock())
    deal = await create(CreateDealCommand(Decimal(100), "EUR", "USD"))

    assert deal.converted_amount == Decimal("112.16")


async def test_usd_to_byn() -> None:
    create = CreateDeal(make_uow(), FixedClock())
    deal = await create(CreateDealCommand(Decimal(100), "USD", "BYN"))

    assert deal.to_currency == BYN
    assert deal.converted_amount == Decimal("300.91")


async def test_byn_to_usd() -> None:
    create = CreateDeal(make_uow(), FixedClock())
    deal = await create(CreateDealCommand(Decimal("300.91"), "BYN", "USD"))

    assert deal.converted_amount == Decimal("100.00")


async def test_unknown_currency_raises_unsupported() -> None:
    uow = make_uow()
    create = CreateDeal(uow, FixedClock())

    with pytest.raises(UnsupportedCurrencyError):
        await create(CreateDealCommand(Decimal(100), "USD", "JPY"))

    assert uow.deals.deals == {}
    assert uow.commits == 0


async def test_no_rates_today_raises_not_available() -> None:
    create = CreateDeal(FakeUnitOfWork(), FixedClock())

    with pytest.raises(RatesNotAvailableError):
        await create(CreateDealCommand(Decimal(100), "USD", "EUR"))


async def test_rates_from_yesterday_are_not_used() -> None:
    yesterday = TODAY - timedelta(days=1)
    rates = InMemoryRateRepository(
        [
            make_rate("USD", "3.0091", on_date=yesterday),
            make_rate("EUR", "3.3749", on_date=yesterday),
        ]
    )
    create = CreateDeal(FakeUnitOfWork(rates=rates), FixedClock())

    with pytest.raises(RatesNotAvailableError):
        await create(CreateDealCommand(Decimal(100), "USD", "EUR"))


async def test_invalid_code_raises_currency_code_error() -> None:
    create = CreateDeal(make_uow(), FixedClock())

    with pytest.raises(CurrencyCodeError):
        await create(CreateDealCommand(Decimal(100), "usd", "EUR"))


async def test_domain_error_saves_nothing() -> None:
    uow = make_uow()
    create = CreateDeal(uow, FixedClock())

    with pytest.raises(SameCurrencyExchangeError):
        await create(CreateDealCommand(Decimal(100), "USD", "USD"))

    assert uow.deals.deals == {}
    assert uow.commits == 0
