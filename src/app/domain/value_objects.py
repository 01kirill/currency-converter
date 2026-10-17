import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.domain.exceptions import (
    CurrencyCodeError,
    RateNotFiniteError,
    RateValueError,
    ScaleValueError,
)

_CODE_RE = re.compile(r"[A-Z]{3}")


class DealStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


@dataclass(frozen=True, slots=True)
class CurrencyCode:
    code: str

    def __post_init__(self) -> None:
        if not _CODE_RE.fullmatch(self.code):
            raise CurrencyCodeError(self.code)


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    rate_date: date
    currency_code: CurrencyCode
    scale: int
    rate: Decimal

    def __post_init__(self) -> None:
        if self.scale <= 0:
            raise ScaleValueError()
        if not self.rate.is_finite():
            raise RateNotFiniteError()
        if self.rate <= 0:
            raise RateValueError()

    @property
    def rate_per_unit(self) -> Decimal:
        return self.rate / self.scale
