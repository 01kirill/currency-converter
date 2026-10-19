from datetime import date
from decimal import Decimal
from uuid import UUID


class DomainError(Exception):
    """Base domain exception"""


class InvalidValueError(DomainError):
    pass


class CurrencyCodeError(InvalidValueError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Invalid currency code: {code!r}")


class ScaleNonPositiveValueError(InvalidValueError):
    def __init__(self) -> None:
        super().__init__("Scale value must be positive")


class RateNonPositiveValueError(InvalidValueError):
    def __init__(self) -> None:
        super().__init__("Rate value must be positive")


class RateNotFiniteError(InvalidValueError):
    def __init__(self) -> None:
        super().__init__("Rate value must be finite")


class AmountNonPositiveValueError(InvalidValueError):
    def __init__(self) -> None:
        super().__init__("Amount value must be positive")


class AmountPrecisionError(InvalidValueError):
    def __init__(self, places: int) -> None:
        super().__init__(f"Amount value must have at most {places} decimal places")


class AmountNotFiniteError(InvalidValueError):
    def __init__(self) -> None:
        super().__init__("Amount value must be finite")


class AmountTooBigError(InvalidValueError):
    def __init__(self, max_amount: Decimal) -> None:
        super().__init__(f"Amount value must not exceed {max_amount:f}")


class ConvertedAmountTooSmallError(InvalidValueError):
    def __init__(self) -> None:
        super().__init__("Amount value too small: converted amount rounds to zero")


class SameCurrencyExchangeError(InvalidValueError):
    def __init__(self) -> None:
        super().__init__("Initial currency must differ from target currency")


class RateDateMismatchError(InvalidValueError):
    def __init__(self) -> None:
        super().__init__("Exchange rates must be on the same date")


class UnsupportedCurrencyError(InvalidValueError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Currency {code!r} is not supported")


class InvalidPeriodError(InvalidValueError):
    def __init__(self) -> None:
        super().__init__("date_from must not be later than date_to")


class NotFoundError(DomainError):
    pass


class DealNotFoundError(NotFoundError):
    def __init__(self, deal_id: UUID) -> None:
        super().__init__(f"Deal with id {deal_id} not found")


class ConflictError(DomainError):
    pass


class DealAlreadyResolvedError(ConflictError):
    def __init__(self, deal_id: UUID) -> None:
        super().__init__(f"Conclusion for deal with id {deal_id} already made")


class UnavailableError(DomainError):
    pass


class RatesNotAvailableError(UnavailableError):
    def __init__(self, on_date: date) -> None:
        super().__init__(f"Exchange rates for {on_date} are not loaded yet")
