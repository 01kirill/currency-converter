from datetime import timedelta
from uuid import uuid4

import pytest

from app.application.dto import ResolveDealCommand
from app.application.use_cases.resolve_deal import ResolveDeal
from app.domain.entities import Deal
from app.domain.exceptions import DealAlreadyResolvedError, DealNotFoundError
from app.domain.value_objects import DealStatus
from tests.fakes import NOW, FakeUnitOfWork, FixedClock, InMemoryDealRepository, make_deal

CREATED_AT = NOW - timedelta(minutes=5)


def make_uow(deal: Deal) -> FakeUnitOfWork:
    return FakeUnitOfWork(deals=InMemoryDealRepository([deal]))


async def test_accept_marks_deal_accepted_and_saves_it() -> None:
    deal = make_deal(CREATED_AT)
    uow = make_uow(deal)
    resolve = ResolveDeal(uow, FixedClock())

    result = await resolve(ResolveDealCommand(deal.id, accept=True))

    stored = uow.deals.deals[deal.id]
    assert stored.status is DealStatus.ACCEPTED
    assert stored.resolved_at == NOW
    assert result.status is DealStatus.ACCEPTED
    assert uow.commits == 1


async def test_decline_marks_deal_declined_and_saves_it() -> None:
    deal = make_deal(CREATED_AT)
    uow = make_uow(deal)
    resolve = ResolveDeal(uow, FixedClock())

    result = await resolve(ResolveDealCommand(deal.id, accept=False))

    stored = uow.deals.deals[deal.id]
    assert stored.status is DealStatus.DECLINED
    assert stored.resolved_at == NOW
    assert result.status is DealStatus.DECLINED
    assert uow.commits == 1


async def test_unknown_id_raises_not_found() -> None:
    uow = FakeUnitOfWork()
    resolve = ResolveDeal(uow, FixedClock())

    with pytest.raises(DealNotFoundError):
        await resolve(ResolveDealCommand(uuid4(), accept=True))

    assert uow.commits == 0


@pytest.mark.parametrize("accept", [True, False])
async def test_already_resolved_deal_raises_conflict_and_stays_unchanged(accept: bool) -> None:
    deal = make_deal(CREATED_AT)
    deal.accept(CREATED_AT)
    uow = make_uow(deal)
    resolve = ResolveDeal(uow, FixedClock())

    with pytest.raises(DealAlreadyResolvedError):
        await resolve(ResolveDealCommand(deal.id, accept=accept))

    stored = uow.deals.deals[deal.id]
    assert stored.status is DealStatus.ACCEPTED
    assert stored.resolved_at == CREATED_AT
    assert uow.commits == 0
