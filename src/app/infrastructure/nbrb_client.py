from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.domain.exceptions import InvalidValueError, RatesNotAvailableError
from app.domain.value_objects import CurrencyCode, ExchangeRate


class NbrbRatesProvider:
    """Official daily rates from the NBRB API (https://api.nbrb.by/exrates/rates)"""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(self, on_date: date) -> list[ExchangeRate]:
        """Rates for on_date, any network, HTTP or data problem becomes RatesNotAvailableError"""
        params = {"periodicity": "0", "ondate": on_date.isoformat()}

        try:
            response = await self._client.get("/exrates/rates", params=params)
            response.raise_for_status()
            rates = [_to_rate(item, on_date) for item in response.json()]
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            InvalidOperation,
            InvalidValueError,
        ) as e:
            raise RatesNotAvailableError(on_date) from e
        if not rates:
            raise RatesNotAvailableError(on_date)
        return rates


def _to_rate(item: dict[str, Any], on_date: date) -> ExchangeRate:
    return ExchangeRate(
        rate_date=on_date,
        currency_code=CurrencyCode(item["Cur_Abbreviation"]),
        scale=int(item["Cur_Scale"]),
        rate=Decimal(str(item["Cur_OfficialRate"])),
    )
