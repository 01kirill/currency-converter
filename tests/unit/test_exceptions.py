import pytest

from app.domain.exceptions import (
    AmountNonPositiveValueError,
    AmountNotFiniteError,
    AmountPrecisionError,
    AmountTooBigError,
    ConflictError,
    ConvertedAmountTooSmallError,
    CurrencyCodeError,
    DealAlreadyResolvedError,
    DealNotFoundError,
    DomainError,
    InvalidPeriodError,
    InvalidValueError,
    NotFoundError,
    RateDateMismatchError,
    RateNonPositiveValueError,
    RateNotFiniteError,
    RatesNotAvailableError,
    SameCurrencyExchangeError,
    ScaleNonPositiveValueError,
    UnavailableError,
    UnsupportedCurrencyError,
)


@pytest.mark.parametrize(
    ("error_class", "group"),
    [
        (CurrencyCodeError, InvalidValueError),
        (ScaleNonPositiveValueError, InvalidValueError),
        (RateNonPositiveValueError, InvalidValueError),
        (RateNotFiniteError, InvalidValueError),
        (AmountNonPositiveValueError, InvalidValueError),
        (AmountNotFiniteError, InvalidValueError),
        (AmountPrecisionError, InvalidValueError),
        (AmountTooBigError, InvalidValueError),
        (ConvertedAmountTooSmallError, InvalidValueError),
        (SameCurrencyExchangeError, InvalidValueError),
        (RateDateMismatchError, InvalidValueError),
        (DealNotFoundError, NotFoundError),
        (DealAlreadyResolvedError, ConflictError),
        (RatesNotAvailableError, UnavailableError),
        (UnsupportedCurrencyError, InvalidValueError),
        (InvalidPeriodError, InvalidValueError),
    ],
)
def test_domain_error_belongs_to_its_group(
    error_class: type[DomainError], group: type[DomainError]
) -> None:
    assert issubclass(error_class, group)


@pytest.mark.parametrize(
    "group",
    [
        InvalidValueError,
        NotFoundError,
        ConflictError,
        UnavailableError,
    ],
)
def test_error_groups_inherit_from_domain_error(group: type[DomainError]) -> None:
    assert issubclass(group, DomainError)


def test_domain_error_is_regular_exception() -> None:
    assert issubclass(DomainError, Exception)
