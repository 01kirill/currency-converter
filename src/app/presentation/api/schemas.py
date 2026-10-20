from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from app.application.dto import CreateDealCommand, CurrencyReportRow
from app.domain.entities import Deal
from app.domain.value_objects import DealStatus


class CreateDealRequest(BaseModel):
    amount: Decimal = Field(examples=["100.00"])
    from_currency: str = Field(examples=["USD"])
    to_currency: str = Field(examples=["EUR"])

    def to_command(self) -> CreateDealCommand:
        return CreateDealCommand(self.amount, self.from_currency, self.to_currency)


class ResolveDealRequest(BaseModel):
    accept: bool


class DealResponse(BaseModel):
    id: UUID
    amount: Decimal
    from_currency: str
    to_currency: str
    rate: Decimal
    converted_amount: Decimal
    status: DealStatus
    created_at: datetime
    resolved_at: datetime | None

    @classmethod
    def from_domain(cls, deal: Deal) -> Self:
        return cls(
            id=deal.id,
            amount=deal.amount,
            from_currency=deal.from_currency.code,
            to_currency=deal.to_currency.code,
            rate=deal.rate,
            converted_amount=deal.converted_amount,
            status=deal.status,
            created_at=deal.created_at,
            resolved_at=deal.resolved_at,
        )


class CurrencyReportRowResponse(BaseModel):
    currency: str
    received_amount: Decimal
    paid_out_amount: Decimal
    deals_count: int

    @classmethod
    def from_domain(cls, row: CurrencyReportRow) -> Self:
        return cls(
            currency=row.currency.code,
            received_amount=row.received_amount,
            paid_out_amount=row.paid_out_amount,
            deals_count=row.deals_count,
        )


class ErrorResponse(BaseModel):
    detail: str
