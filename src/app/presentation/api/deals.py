from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.application.dto import ResolveDealCommand
from app.application.use_cases.create_deal import CreateDeal
from app.application.use_cases.list_pending_deals import ListPendingDeals
from app.application.use_cases.resolve_deal import ResolveDeal
from app.dependencies import get_create_deal, get_list_pending_deals, get_resolve_deal
from app.presentation.api.errors import error_responses
from app.presentation.api.schemas import (
    CreateDealRequest,
    DealResponse,
    ResolveDealRequest,
)

router = APIRouter(prefix="/deals", tags=["deals"])


@router.post("", status_code=status.HTTP_201_CREATED, responses=error_responses(422, 503))
async def create_deal(
    body: CreateDealRequest,
    create: Annotated[CreateDeal, Depends(get_create_deal)],
) -> DealResponse:
    """Quote an exchange at today's NBRB rates, the deal waits for the client's decision"""
    deal = await create(body.to_command())
    return DealResponse.from_domain(deal)


@router.get("/pending")
async def list_pending_deals(
    list_pending: Annotated[ListPendingDeals, Depends(get_list_pending_deals)],
) -> list[DealResponse]:
    """Deals awaiting the client's decision, oldest first"""
    return [DealResponse.from_domain(deal) for deal in await list_pending()]


@router.post("/{deal_id}/resolve", responses=error_responses(404, 409))
async def resolve_deal(
    deal_id: UUID,
    body: ResolveDealRequest,
    resolve: Annotated[ResolveDeal, Depends(get_resolve_deal)],
) -> DealResponse:
    """Accept or decline a pending deal"""
    deal = await resolve(ResolveDealCommand(deal_id, body.accept))
    return DealResponse.from_domain(deal)
