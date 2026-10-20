from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.domain.exceptions import RatesNotAvailableError
from app.domain.value_objects import CurrencyCode, ExchangeRate
from app.infrastructure.nbrb_client import NbrbRatesProvider

ON_DATE = date(2026, 10, 20)
USD_JSON = {
    "Cur_ID": 431,
    "Date": "2026-10-20T00:00:00",
    "Cur_Abbreviation": "USD",
    "Cur_Scale": 1,
    "Cur_Name": "Доллар США",
    "Cur_OfficialRate": 2.995,
}
RUB_JSON = {
    "Cur_ID": 456,
    "Date": "2026-10-20T00:00:00",
    "Cur_Abbreviation": "RUB",
    "Cur_Scale": 100,
    "Cur_Name": "Российских рублей",
    "Cur_OfficialRate": 3.6127,
}

Handler = Callable[[httpx.Request], httpx.Response]


def make_provider(handler: Handler) -> NbrbRatesProvider:
    transport = httpx.MockTransport(handler)
    return NbrbRatesProvider(httpx.AsyncClient(transport=transport, base_url="https://api.nbrb.by"))


def respond(status_code: int = 200, **kwargs: Any) -> Handler:
    return lambda request: httpx.Response(status_code, **kwargs)


async def test_maps_response_to_domain_rates() -> None:
    provider = make_provider(respond(json=[USD_JSON, RUB_JSON]))

    rates = await provider.fetch(ON_DATE)

    assert rates == [
        ExchangeRate(ON_DATE, CurrencyCode("USD"), 1, Decimal("2.995")),
        ExchangeRate(ON_DATE, CurrencyCode("RUB"), 100, Decimal("3.6127")),
    ]


async def test_requests_daily_rates_on_given_date() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[USD_JSON])

    await make_provider(handler).fetch(ON_DATE)

    [request] = requests
    assert request.method == "GET"
    assert request.url.path == "/exrates/rates"
    assert request.url.params["periodicity"] == "0"
    assert request.url.params["ondate"] == "2026-10-20"


async def test_empty_response_raises_not_available() -> None:
    provider = make_provider(respond(json=[]))

    with pytest.raises(RatesNotAvailableError):
        await provider.fetch(ON_DATE)


@pytest.mark.parametrize("status_code", [404, 500, 503])
async def test_error_status_raises_not_available(status_code: int) -> None:
    provider = make_provider(respond(status_code))

    with pytest.raises(RatesNotAvailableError) as exc_info:
        await provider.fetch(ON_DATE)

    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


async def test_network_error_raises_not_available() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(RatesNotAvailableError) as exc_info:
        await make_provider(handler).fetch(ON_DATE)

    assert isinstance(exc_info.value.__cause__, httpx.ConnectTimeout)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"text": "<html>maintenance</html>"},
        {"json": {"error": "unexpected object"}},
        {"json": [{**USD_JSON, "Cur_OfficialRate": None}]},
        {"json": [{k: v for k, v in USD_JSON.items() if k != "Cur_Scale"}]},
        {"json": [{**USD_JSON, "Cur_OfficialRate": -1}]},
        {"json": [{**USD_JSON, "Cur_Abbreviation": "usd"}]},
    ],
    ids=["not-json", "object", "null-rate", "no-scale", "negative-rate", "bad-code"],
)
async def test_malformed_body_raises_not_available(kwargs: dict[str, Any]) -> None:
    provider = make_provider(respond(**kwargs))

    with pytest.raises(RatesNotAvailableError):
        await provider.fetch(ON_DATE)
