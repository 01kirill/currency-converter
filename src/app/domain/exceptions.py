class DomainError(Exception):
    """Base domain exception"""


class CurrencyCodeError(DomainError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Invalid currency code: {code!r}")


class ScaleValueError(DomainError):
    def __init__(self) -> None:
        super().__init__("Scale value must be positive")


class RateValueError(DomainError):
    def __init__(self) -> None:
        super().__init__("Rate value must be positive")


class RateNotFiniteError(DomainError):
    def __init__(self) -> None:
        super().__init__("Rate value must be finite")
