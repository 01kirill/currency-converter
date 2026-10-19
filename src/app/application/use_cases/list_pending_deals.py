from app.application.ports import UnitOfWork
from app.domain.entities import Deal


class ListPendingDeals:
    """Deals awaiting the client's decision"""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def __call__(self) -> list[Deal]:
        async with self._uow:
            return await self._uow.deals.list_pending()
