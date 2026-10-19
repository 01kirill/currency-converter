from app.application.dto import CurrencyReportRow, DealReportQuery
from app.application.ports import UnitOfWork
from app.domain.exceptions import InvalidPeriodError
from app.domain.value_objects import CurrencyCode


class GetDealsReport:
    """Cash totals per currency over accepted deals for a period"""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def __call__(self, query: DealReportQuery) -> list[CurrencyReportRow]:
        if query.date_from > query.date_to:
            raise InvalidPeriodError()

        currency = CurrencyCode(query.currency) if query.currency is not None else None
        async with self._uow:
            return await self._uow.deals.report(query.date_from, query.date_to, currency)
