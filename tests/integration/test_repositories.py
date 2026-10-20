import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.dto import CreateDealCommand, ResolveDealCommand
from app.application.use_cases.create_deal import CreateDeal
from app.application.use_cases.resolve_deal import ResolveDeal
from app.domain.entities import Deal
from app.domain.exceptions import DealAlreadyResolvedError
from app.domain.value_objects import CurrencyCode, DealStatus
from app.infrastructure.clock import MINSK
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from tests.fakes import NOW, TODAY, FixedClock, make_deal, make_rate

USD = make_rate("USD", "3.0091")
EUR = make_rate("EUR", "3.3749")
RUB = make_rate("RUB", "3.6038", scale=100)


async def save(uow: SqlAlchemyUnitOfWork, *deals: Deal) -> None:
    async with uow:
        for deal in deals:
            await uow.deals.add(deal)
        await uow.commit()


def accepted_deal(amount: str, from_code: str, to_code: str, resolved_at: datetime) -> Deal:
    rates = {"USD": USD, "EUR": EUR, "RUB": RUB}
    deal = Deal.create(Decimal(amount), rates[from_code], rates[to_code], NOW)
    deal.accept(resolved_at)
    return deal


async def test_rates_saved_twice_are_not_duplicated(uow: SqlAlchemyUnitOfWork) -> None:
    async with uow:
        await uow.rates.add_many([USD, RUB])
        await uow.commit()
    async with uow:
        await uow.rates.add_many([USD, EUR])
        await uow.commit()

    async with uow:
        assert await uow.rates.exists(TODAY)
        assert not await uow.rates.exists(TODAY - timedelta(days=1))
        assert await uow.rates.get(CurrencyCode("USD"), TODAY) == USD
        assert await uow.rates.get(CurrencyCode("RUB"), TODAY) == RUB
        assert await uow.rates.get(CurrencyCode("EUR"), TODAY) == EUR
        assert await uow.rates.get(CurrencyCode("JPY"), TODAY) is None


async def test_add_many_with_empty_list_does_nothing(uow: SqlAlchemyUnitOfWork) -> None:
    async with uow:
        await uow.rates.add_many([])
        await uow.commit()

    async with uow:
        assert not await uow.rates.exists(TODAY)


async def test_deal_round_trip_keeps_all_fields(uow: SqlAlchemyUnitOfWork) -> None:
    deal = make_deal()
    await save(uow, deal)

    async with uow:
        loaded = await uow.deals.get_for_update(deal.id)

    assert loaded is not None
    assert loaded.id == deal.id
    assert loaded.amount == deal.amount
    assert loaded.rate == deal.rate
    assert loaded.from_currency == deal.from_currency
    assert loaded.to_currency == deal.to_currency
    assert loaded.converted_amount == deal.converted_amount
    assert loaded.status is DealStatus.PENDING
    assert loaded.created_at == deal.created_at
    assert loaded.resolved_at is None


async def test_update_saves_status_and_resolved_at(uow: SqlAlchemyUnitOfWork) -> None:
    deal = make_deal()
    await save(uow, deal)

    async with uow:
        loaded = await uow.deals.get_for_update(deal.id)
        assert loaded is not None
        loaded.accept(NOW)
        await uow.deals.update(loaded)
        await uow.commit()

    async with uow:
        stored = await uow.deals.get_for_update(deal.id)
    assert stored is not None
    assert stored.status is DealStatus.ACCEPTED
    assert stored.resolved_at == NOW


async def test_changes_without_commit_are_rolled_back(uow: SqlAlchemyUnitOfWork) -> None:
    deal = make_deal()
    async with uow:
        await uow.deals.add(deal)
        await uow.rates.add_many([USD])

    async with uow:
        assert await uow.deals.get_for_update(deal.id) is None
        assert not await uow.rates.exists(TODAY)


async def test_list_pending_returns_only_pending_oldest_first(uow: SqlAlchemyUnitOfWork) -> None:
    newer = make_deal(NOW)
    older = make_deal(NOW - timedelta(hours=1))
    accepted = make_deal(NOW)
    accepted.accept(NOW)
    await save(uow, newer, older, accepted)

    async with uow:
        pending = await uow.deals.list_pending()

    assert [d.id for d in pending] == [older.id, newer.id]


async def test_report_sums_received_and_paid_out_per_currency(uow: SqlAlchemyUnitOfWork) -> None:
    usd_to_eur = accepted_deal("100", "USD", "EUR", NOW)
    eur_to_usd = accepted_deal("50", "EUR", "USD", NOW)
    declined = Deal.create(Decimal(1000), USD, EUR, NOW)
    declined.decline(NOW)
    pending = Deal.create(Decimal(1000), USD, EUR, NOW)
    await save(uow, usd_to_eur, eur_to_usd, declined, pending)

    async with uow:
        rows = await uow.deals.report(TODAY, TODAY, None)

    by_code = {row.currency.code: row for row in rows}
    assert list(by_code) == ["EUR", "USD"]
    assert by_code["USD"].received_amount == Decimal("100.00")
    assert by_code["USD"].paid_out_amount == eur_to_usd.converted_amount
    assert by_code["USD"].deals_count == 2
    assert by_code["EUR"].received_amount == Decimal("50.00")
    assert by_code["EUR"].paid_out_amount == usd_to_eur.converted_amount
    assert by_code["EUR"].deals_count == 2


async def test_report_filters_by_currency(uow: SqlAlchemyUnitOfWork) -> None:
    await save(
        uow,
        accepted_deal("100", "USD", "EUR", NOW),
        accepted_deal("100", "RUB", "EUR", NOW),
    )

    async with uow:
        rows = await uow.deals.report(TODAY, TODAY, CurrencyCode("RUB"))

    assert [(r.currency.code, r.received_amount, r.deals_count) for r in rows] == [
        ("RUB", Decimal("100.00"), 1)
    ]


async def test_report_uses_minsk_day_boundaries(uow: SqlAlchemyUnitOfWork) -> None:
    before_midnight = datetime(2026, 10, 19, 23, 59, tzinfo=MINSK)
    after_midnight = datetime(2026, 10, 20, 0, 30, tzinfo=MINSK)
    await save(
        uow,
        accepted_deal("100", "USD", "EUR", before_midnight),
        accepted_deal("200", "USD", "EUR", after_midnight),
    )
    next_day = TODAY + timedelta(days=1)

    async with uow:
        on_19th = await uow.deals.report(TODAY, TODAY, CurrencyCode("USD"))
        on_20th = await uow.deals.report(next_day, next_day, CurrencyCode("USD"))

    assert [r.received_amount for r in on_19th] == [Decimal("100.00")]
    assert [r.received_amount for r in on_20th] == [Decimal("200.00")]


async def wait_for_lock_waiter(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Return once another connection is blocked on a row lock, fail after 5 seconds"""
    query = text(
        "SELECT count(*) FROM pg_stat_activity"
        " WHERE wait_event_type = 'Lock' AND datname = current_database()"
    )
    async with session_factory() as session:
        for _ in range(50):
            if await session.scalar(query):
                return
            await session.rollback()  # pg_stat_activity is a per-transaction snapshot
            await asyncio.sleep(0.1)
    raise AssertionError("no transaction waited for the row lock")


async def test_concurrent_resolve_is_blocked_until_first_commits(
    uow: SqlAlchemyUnitOfWork,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    deal = make_deal()
    await save(uow, deal)
    other = SqlAlchemyUnitOfWork(session_factory)

    async def lock_in_parallel() -> None:
        async with other:
            await other.deals.get_for_update(deal.id)

    async with uow:
        locked = await uow.deals.get_for_update(deal.id)
        assert locked is not None

        second = asyncio.create_task(lock_in_parallel())
        await wait_for_lock_waiter(session_factory)
        assert not second.done()

        locked.accept(NOW)
        await uow.deals.update(locked)
        await uow.commit()

    await asyncio.wait_for(second, timeout=5)


async def test_use_cases_work_with_real_unit_of_work(uow: SqlAlchemyUnitOfWork) -> None:
    async with uow:
        await uow.rates.add_many([USD, EUR])
        await uow.commit()

    deal = await CreateDeal(uow, FixedClock())(CreateDealCommand(Decimal(100), "USD", "EUR"))
    resolved = await ResolveDeal(uow, FixedClock())(ResolveDealCommand(deal.id, accept=True))

    assert resolved.status is DealStatus.ACCEPTED
    with pytest.raises(DealAlreadyResolvedError):
        await ResolveDeal(uow, FixedClock())(ResolveDealCommand(deal.id, accept=False))
