from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID, uuid4

from app.domain.exceptions import DealAlreadyResolvedError
from app.domain.value_objects import CurrencyCode, DealStatus, ExchangeRate, convert


@dataclass(slots=True, eq=False)
class Deal:
    """Exchange deal with a quote fixed at creation; equal by id, resolved exactly once"""

    id: UUID
    amount: Decimal
    rate: Decimal
    from_currency: CurrencyCode
    to_currency: CurrencyCode
    converted_amount: Decimal
    status: DealStatus
    created_at: datetime
    resolved_at: datetime | None = None

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Deal) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def accept(self, now: datetime) -> None:
        if self.status != DealStatus.PENDING:
            raise DealAlreadyResolvedError(self.id)
        self.status = DealStatus.ACCEPTED
        self.resolved_at = now

    def decline(self, now: datetime) -> None:
        if self.status != DealStatus.PENDING:
            raise DealAlreadyResolvedError(self.id)
        self.status = DealStatus.DECLINED
        self.resolved_at = now

    @classmethod
    def create(
        cls,
        amount: Decimal,
        from_rate: ExchangeRate,
        to_rate: ExchangeRate,
        now: datetime,
    ) -> Self:
        conversion = convert(amount, from_rate, to_rate)
        return cls(
            id=uuid4(),
            amount=amount,
            from_currency=from_rate.currency_code,
            to_currency=to_rate.currency_code,
            rate=conversion.rate,
            converted_amount=conversion.converted_amount,
            status=DealStatus.PENDING,
            created_at=now,
        )
