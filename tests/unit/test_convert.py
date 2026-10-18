from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pytest

from app.domain.exceptions import (
    AmountNonPositiveValueError,
    AmountNotFiniteError,
    AmountPrecisionError,
    AmountTooBigError,
    ConvertedAmountTooSmallError,
    DomainError,
    RateDateMismatchError,
    SameCurrencyExchangeError,
)
from app.domain.value_objects import (
    AMOUNT_PRECISION,
    BYN,
    MAX_AMOUNT,
    CurrencyCode,
    ExchangeRate,
    convert,
)

RATE_DATE = date(2026, 10, 17)


def make_rate(code: str, rate: str, scale: int = 1, rate_date: date = RATE_DATE) -> ExchangeRate:
    """Build a rate the way NBRB publishes it: rate BYN for scale units of code"""
    return ExchangeRate(
        rate_date=rate_date, currency_code=CurrencyCode(code), scale=scale, rate=Decimal(rate)
    )


USD_RATE = make_rate("USD", "3.0091")
EUR_RATE = make_rate("EUR", "3.3749")
RUB_RATE = make_rate("RUB", "3.6038", scale=100)
CZK_RATE = make_rate("CZK", "13.8598", scale=100)
IRR_RATE = make_rate("IRR", "0.1681", scale=100000)
VND_RATE = make_rate("VND", "11.6303", scale=100000)
BYN_RATE = ExchangeRate(rate_date=RATE_DATE, currency_code=BYN, scale=1, rate=Decimal(1))


@pytest.mark.parametrize(
    ("amount", "from_rate", "to_rate", "expected_rate", "expected_amount"),
    [
        ("100", USD_RATE, EUR_RATE, "0.8916116033", "89.16"),
        ("100", USD_RATE, BYN_RATE, "3.0091", "300.91"),
        ("100", BYN_RATE, USD_RATE, "0.3323252800", "33.23"),
        ("1000", RUB_RATE, USD_RATE, "0.01197633844", "11.98"),
        ("1000000", IRR_RATE, USD_RATE, "5.586387957E-7", "0.56"),
        ("1000000", VND_RATE, USD_RATE, "0.00003865042704", "38.65"),
    ],
    ids=[
        "cross-rate-via-byn",
        "to-byn",
        "from-byn",
        "scale-100",
        "scale-100000-irr",
        "scale-100000-vnd",
    ],
)
def test_convert_calculates_rate_and_amount(
    amount: str,
    from_rate: ExchangeRate,
    to_rate: ExchangeRate,
    expected_rate: str,
    expected_amount: str,
) -> None:
    result = convert(Decimal(amount), from_rate, to_rate)
    assert result.rate == Decimal(expected_rate)
    assert result.converted_amount == Decimal(expected_amount)


def test_convert_keeps_ten_significant_digits_for_tiny_rates() -> None:
    rate = convert(Decimal(1000000), IRR_RATE, USD_RATE).rate
    assert len(rate.as_tuple().digits) == 10


def test_convert_amount_is_reproducible_from_returned_rate() -> None:
    amount = Decimal("123.45")
    result = convert(amount, USD_RATE, EUR_RATE)
    assert (amount * result.rate).quantize(AMOUNT_PRECISION, ROUND_HALF_UP) == (
        result.converted_amount
    )


def test_convert_rounds_half_up() -> None:
    from_rate = make_rate("USD", "1.005")
    assert convert(Decimal(1), from_rate, BYN_RATE).converted_amount == Decimal("1.01")


@pytest.mark.parametrize(
    "amount",
    ["0.01", "10.10", "10.100", str(MAX_AMOUNT)],
    ids=["minimal", "one-trailing-zero", "extra-trailing-zeros", "maximal"],
)
def test_convert_accepts_valid_amount(amount: str) -> None:
    assert convert(Decimal(amount), USD_RATE, BYN_RATE).converted_amount > 0


@pytest.mark.parametrize(
    ("amount", "error"),
    [
        ("NaN", AmountNotFiniteError),
        ("Infinity", AmountNotFiniteError),
        ("0", AmountNonPositiveValueError),
        ("-1", AmountNonPositiveValueError),
        ("10.123", AmountPrecisionError),
        (str(MAX_AMOUNT + 1), AmountTooBigError),
        ("1e30", AmountTooBigError),
    ],
    ids=["nan", "infinity", "zero", "negative", "three-decimals", "above-max", "huge"],
)
def test_convert_rejects_invalid_amount(amount: str, error: type[DomainError]) -> None:
    with pytest.raises(error):
        convert(Decimal(amount), USD_RATE, BYN_RATE)


def test_convert_rejects_amount_that_rounds_to_zero() -> None:
    with pytest.raises(ConvertedAmountTooSmallError):
        convert(Decimal("0.01"), CZK_RATE, USD_RATE)


def test_convert_rejects_same_currency() -> None:
    with pytest.raises(SameCurrencyExchangeError):
        convert(Decimal(100), USD_RATE, USD_RATE)


def test_convert_rejects_rates_on_different_dates() -> None:
    eur_next_day = make_rate("EUR", "3.3749", rate_date=date(2026, 10, 18))
    with pytest.raises(RateDateMismatchError):
        convert(Decimal(100), USD_RATE, eur_next_day)
