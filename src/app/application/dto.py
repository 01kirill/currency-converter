from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.value_objects import CurrencyCode


@dataclass(frozen=True, slots=True)
class CreateDealCommand:
    """Input of CreateDeal: raw client values, validated by the domain"""

    amount: Decimal
    from_currency: str
    to_currency: str


@dataclass(frozen=True, slots=True)
class ResolveDealCommand:
    """Input of ResolveDeal: accept=True accepts the deal, False declines it"""

    deal_id: UUID
    accept: bool


@dataclass(frozen=True, slots=True)
class DealReportQuery:
    """Input of GetDealsReport: inclusive period in Minsk dates, optional currency"""

    date_from: date
    date_to: date
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class CurrencyReportRow:
    """Cash totals for one currency over accepted deals

    A deal counts for both its currencies,
    so deals_count summed over all rows is twice the number of deals
    """

    currency: CurrencyCode
    received_amount: Decimal
    paid_out_amount: Decimal
    deals_count: int
