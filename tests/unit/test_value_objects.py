import dataclasses
import re
from datetime import date
from decimal import Decimal

import pytest

from app.domain.exceptions import (
    CurrencyCodeError,
    DomainError,
    RateNotFiniteError,
    RateValueError,
    ScaleValueError,
)
from app.domain.value_objects import CurrencyCode, DealStatus, ExchangeRate

RATE_DATE = date(2026, 10, 17)
USD = CurrencyCode("USD")


def make_rate(scale: int = 1, rate: Decimal = Decimal("3.0091")) -> ExchangeRate:
    """Build a valid rate, overriding only the fields a test cares about."""
    return ExchangeRate(rate_date=RATE_DATE, currency_code=USD, scale=scale, rate=rate)


@pytest.mark.parametrize("code", ["USD", "BYN", "EUR", "XDR"])
def test_currency_code_accepts_valid_iso_code(code: str) -> None:
    assert CurrencyCode(code).code == code


@pytest.mark.parametrize(
    "code",
    [
        "usd",
        "Usd",
        "US",
        "USDX",
        "",
        "U1D",
        "840",
        "12$",
        "US-",
        "U D",
        " USD",
        "USD ",
        "USD\n",
        "\nUSD",
        "USD\t",
        "ÄÖÜ",
        "\uff35\uff33\uff24",
        "US\u0421",
    ],
    ids=[
        "lowercase",
        "mixed-case",
        "too-short",
        "too-long",
        "empty",
        "digit-inside",
        "numeric-iso-code",
        "special-chars",
        "dash",
        "inner-space",
        "leading-space",
        "trailing-space",
        "trailing-newline",
        "leading-newline",
        "tab",
        "non-ascii-latin",
        "full-width",
        "cyrillic-lookalike",
    ],
)
def test_currency_code_rejects_invalid_code(code: str) -> None:
    with pytest.raises(CurrencyCodeError):
        CurrencyCode(code)


def test_currency_code_error_message_shows_repr_of_value() -> None:
    with pytest.raises(CurrencyCodeError, match=re.escape("'USD\\n'")):
        CurrencyCode("USD\n")


def test_currency_code_is_hashable_and_deduplicated_in_set() -> None:
    assert len({CurrencyCode("USD"), CurrencyCode("USD"), CurrencyCode("EUR")}) == 2


def test_currency_code_is_immutable() -> None:
    code = CurrencyCode("USD")
    with pytest.raises(dataclasses.FrozenInstanceError):
        code.code = "EUR"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("scale", "rate", "expected"),
    [
        (1, Decimal("3.0091"), Decimal("3.0091")),
        (100, Decimal("3.7"), Decimal("0.037")),
        (1000, Decimal("8.3357"), Decimal("0.0083357")),
        (100000, Decimal("12.3456"), Decimal("0.000123456")),
    ],
    ids=["scale-1", "scale-100", "scale-1000", "scale-100000"],
)
def test_rate_per_unit_divides_rate_by_scale(scale: int, rate: Decimal, expected: Decimal) -> None:
    assert make_rate(scale=scale, rate=rate).rate_per_unit == expected


def test_rate_per_unit_returns_decimal_for_non_terminating_division() -> None:
    result = make_rate(scale=3, rate=Decimal("1")).rate_per_unit

    assert isinstance(result, Decimal)
    assert result.is_finite()


def test_exchange_rate_accepts_minimal_scale() -> None:
    assert make_rate(scale=1).scale == 1


@pytest.mark.parametrize("scale", [0, -1], ids=["zero", "negative"])
def test_exchange_rate_rejects_non_positive_scale(scale: int) -> None:
    with pytest.raises(ScaleValueError):
        make_rate(scale=scale)


def test_exchange_rate_accepts_minimal_nbrb_rate_step() -> None:
    assert make_rate(rate=Decimal("0.0001")).rate == Decimal("0.0001")


@pytest.mark.parametrize(
    "rate",
    [Decimal("0"), Decimal("-0"), Decimal("-1")],
    ids=["zero", "negative-zero", "negative"],
)
def test_exchange_rate_rejects_non_positive_rate(rate: Decimal) -> None:
    with pytest.raises(RateValueError):
        make_rate(rate=rate)


@pytest.mark.parametrize(
    "rate",
    [Decimal("Infinity"), Decimal("-Infinity"), Decimal("NaN"), Decimal("sNaN")],
    ids=["infinity", "negative-infinity", "nan", "signaling-nan"],
)
def test_exchange_rate_rejects_non_finite_rate(rate: Decimal) -> None:
    with pytest.raises(RateNotFiniteError):
        make_rate(rate=rate)


def test_exchange_rate_checks_scale_before_rate() -> None:
    with pytest.raises(ScaleValueError):
        make_rate(scale=0, rate=Decimal("0"))


def test_exchange_rate_is_immutable() -> None:
    rate = make_rate()
    with pytest.raises(dataclasses.FrozenInstanceError):
        rate.rate = Decimal("1")  # type: ignore[misc]


@pytest.mark.parametrize(
    ("status", "value"),
    [
        (DealStatus.PENDING, "pending"),
        (DealStatus.ACCEPTED, "accepted"),
        (DealStatus.DECLINED, "declined"),
    ],
)
def test_deal_status_values_match_storage_contract(status: DealStatus, value: str) -> None:
    assert status == value
    assert DealStatus(value) is status


def test_deal_status_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        DealStatus("done")


def test_deal_status_has_exactly_three_members() -> None:
    assert len(DealStatus) == 3


@pytest.mark.parametrize(
    "error_class",
    [CurrencyCodeError, ScaleValueError, RateValueError, RateNotFiniteError],
)
def test_domain_errors_inherit_from_domain_error(error_class: type[DomainError]) -> None:
    assert issubclass(error_class, DomainError)


def test_domain_error_is_regular_exception() -> None:
    assert issubclass(DomainError, Exception)
