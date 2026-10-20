from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.dto import DealReportQuery
from app.application.use_cases.get_deals_report import GetDealsReport
from app.dependencies import get_deals_report
from app.presentation.api.errors import error_responses
from app.presentation.api.schemas import CurrencyReportRowResponse

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/deals", responses=error_responses(422))
async def deals_report(
    date_from: date,
    date_to: date,
    report: Annotated[GetDealsReport, Depends(get_deals_report)],
    currency: str | None = None,
) -> list[CurrencyReportRowResponse]:
    """Cash totals per currency over deals accepted within [date_from, date_to], Minsk dates"""
    rows = await report(DealReportQuery(date_from, date_to, currency))
    return [CurrencyReportRowResponse.from_domain(row) for row in rows]
