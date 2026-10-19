import pytest

from app.application.use_cases.load_daily_rates import LoadDailyRates
from app.domain.exceptions import RatesNotAvailableError
from tests.fakes import (
    TODAY,
    FakeRatesProvider,
    FakeUnitOfWork,
    FixedClock,
    InMemoryRateRepository,
    make_rate,
)

USD = make_rate("USD", "3.0091")
EUR = make_rate("EUR", "3.3749")


async def test_loads_and_saves_rates_for_today() -> None:
    uow = FakeUnitOfWork()
    provider = FakeRatesProvider([USD, EUR])
    load = LoadDailyRates(uow, provider, FixedClock())

    loaded = await load()

    assert loaded == 2
    assert provider.calls == [TODAY]
    assert await uow.rates.get(USD.currency_code, TODAY) == USD
    assert await uow.rates.get(EUR.currency_code, TODAY) == EUR
    assert uow.commits == 1


async def test_skips_fetch_when_rates_already_loaded() -> None:
    uow = FakeUnitOfWork(rates=InMemoryRateRepository([USD]))
    provider = FakeRatesProvider([USD, EUR])
    load = LoadDailyRates(uow, provider, FixedClock())

    loaded = await load()

    assert loaded == 0
    assert provider.calls == []
    assert uow.commits == 0


async def test_provider_error_propagates_and_nothing_saved() -> None:
    uow = FakeUnitOfWork()
    provider = FakeRatesProvider([], error=RatesNotAvailableError(TODAY))
    load = LoadDailyRates(uow, provider, FixedClock())

    with pytest.raises(RatesNotAvailableError):
        await load()

    assert not await uow.rates.exists(TODAY)
    assert uow.commits == 0
