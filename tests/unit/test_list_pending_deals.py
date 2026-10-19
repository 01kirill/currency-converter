from app.application.use_cases.list_pending_deals import ListPendingDeals
from tests.fakes import NOW, FakeUnitOfWork, InMemoryDealRepository, make_deal


async def test_returns_pending_deals_without_commit() -> None:
    pending = make_deal()
    accepted = make_deal()
    accepted.accept(NOW)
    uow = FakeUnitOfWork(deals=InMemoryDealRepository([pending, accepted]))
    list_pending = ListPendingDeals(uow)

    result = await list_pending()

    assert result == [pending]
    assert uow.commits == 0


async def test_returns_empty_list_when_no_deals() -> None:
    list_pending = ListPendingDeals(FakeUnitOfWork())

    assert await list_pending() == []
