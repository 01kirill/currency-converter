import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Context, Decimal
from enum import StrEnum

from app.domain.exceptions import (
    AmountNonPositiveValueError,
    AmountNotFiniteError,
    AmountPrecisionError,
    AmountTooBigError,
    ConvertedAmountTooSmallError,
    CurrencyCodeError,
    RateDateMismatchError,
    RateNonPositiveValueError,
    RateNotFiniteError,
    SameCurrencyExchangeError,
    ScaleNonPositiveValueError,
)

_CODE_RE = re.compile(r"[A-Z]{3}")


RATE_CONTEXT = Context(prec=10, rounding=ROUND_HALF_UP)
AMOUNT_DECIMAL_PLACES = 2
AMOUNT_PRECISION = Decimal(10) ** -AMOUNT_DECIMAL_PLACES
MAX_AMOUNT = Decimal("1e12")


@dataclass(frozen=True, slots=True)
class CurrencyCode:
    """ISO 4217 alphabetic currency code: exactly 3 uppercase latin letters"""

    code: str

    def __post_init__(self) -> None:
        if not _CODE_RE.fullmatch(self.code):
            raise CurrencyCodeError(self.code)


BYN = CurrencyCode("BYN")


class DealStatus(StrEnum):
    """Deal lifecycle: pending until the client accepts or declines it, then final"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    """Official NBRB rate on a date: rate BYN for scale units of the currency"""

    rate_date: date
    currency_code: CurrencyCode
    scale: int
    rate: Decimal

    def __post_init__(self) -> None:
        if self.scale <= 0:
            raise ScaleNonPositiveValueError()
        if not self.rate.is_finite():
            raise RateNotFiniteError()
        if self.rate <= 0:
            raise RateNonPositiveValueError()

    @property
    def rate_per_unit(self) -> Decimal:
        return self.rate / self.scale


@dataclass(frozen=True, slots=True)
class Conversion:
    """Result of convert(): cross rate and amount in the target currency"""

    rate: Decimal
    converted_amount: Decimal


def convert(
    amount: Decimal,
    from_rate: ExchangeRate,
    to_rate: ExchangeRate,
) -> Conversion:
    """Convert via BYN: rate = from per-unit / to per-unit, amount rounded HALF_UP to 2 places"""
    if not amount.is_finite():
        raise AmountNotFiniteError()
    if amount > MAX_AMOUNT:
        raise AmountTooBigError(MAX_AMOUNT)
    if amount <= 0:
        raise AmountNonPositiveValueError()
    exponent = amount.normalize().as_tuple().exponent
    if not isinstance(exponent, int) or exponent < -AMOUNT_DECIMAL_PLACES:
        raise AmountPrecisionError(AMOUNT_DECIMAL_PLACES)
    if from_rate.currency_code == to_rate.currency_code:
        raise SameCurrencyExchangeError()
    if from_rate.rate_date != to_rate.rate_date:
        raise RateDateMismatchError()

    rate = RATE_CONTEXT.divide(
        from_rate.rate_per_unit,
        to_rate.rate_per_unit,
    )
    converted = (amount * rate).quantize(
        AMOUNT_PRECISION,
        ROUND_HALF_UP,
    )
    if converted <= 0:
        raise ConvertedAmountTooSmallError()
    return Conversion(rate, converted)
