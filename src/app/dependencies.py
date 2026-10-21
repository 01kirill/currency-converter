from typing import Annotated

from fastapi import Depends, Request

from app.application.ports import Clock, UnitOfWork
from app.application.use_cases.create_deal import CreateDeal
from app.application.use_cases.get_deals_report import GetDealsReport
from app.application.use_cases.list_pending_deals import ListPendingDeals
from app.application.use_cases.resolve_deal import ResolveDeal
from app.infrastructure.clock import MinskClock
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


def get_uow(request: Request) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(request.app.state.session_factory)


def get_clock() -> Clock:
    return MinskClock()


UowDep = Annotated[UnitOfWork, Depends(get_uow)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def get_create_deal(uow: UowDep, clock: ClockDep) -> CreateDeal:
    return CreateDeal(uow, clock)


def get_resolve_deal(uow: UowDep, clock: ClockDep) -> ResolveDeal:
    return ResolveDeal(uow, clock)


def get_list_pending_deals(uow: UowDep) -> ListPendingDeals:
    return ListPendingDeals(uow)


def get_deals_report(uow: UowDep) -> GetDealsReport:
    return GetDealsReport(uow)
