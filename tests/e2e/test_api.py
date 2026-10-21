from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from tests.fakes import TODAY, make_rate

DEALS = "/api/v1/deals"
REPORT = "/api/v1/reports/deals"
USD_TO_EUR = {"amount": "100.00", "from_currency": "USD", "to_currency": "EUR"}


@pytest.fixture
async def rates(uow: SqlAlchemyUnitOfWork) -> None:
    async with uow:
        await uow.rates.add_many(
            [
                make_rate("USD", "3.0091"),
                make_rate("EUR", "3.3749"),
            ]
        )
        await uow.commit()


async def create_deal(client: AsyncClient) -> str:
    response = await client.post(DEALS, json=USD_TO_EUR)
    assert response.status_code == 201
    deal_id: str = response.json()["id"]
    return deal_id


async def resolve(client: AsyncClient, deal_id: str, accept: bool) -> Any:
    return await client.post(f"{DEALS}/{deal_id}/resolve", json={"accept": accept})


async def pending_ids(client: AsyncClient) -> list[str]:
    response = await client.get(f"{DEALS}/pending")
    assert response.status_code == 200
    return [deal["id"] for deal in response.json()]


async def report(client: AsyncClient) -> dict[str, dict[str, Any]]:
    response = await client.get(
        REPORT, params={"date_from": TODAY.isoformat(), "date_to": TODAY.isoformat()}
    )
    assert response.status_code == 200
    return {row["currency"]: row for row in response.json()}


@pytest.mark.usefixtures("rates")
async def test_accepted_deal_goes_from_pending_to_report(client: AsyncClient) -> None:
    created = await client.post(DEALS, json=USD_TO_EUR)

    assert created.status_code == 201
    deal = created.json()
    assert deal["status"] == "pending"
    assert Decimal(deal["converted_amount"]) == Decimal("89.16")
    assert Decimal(deal["rate"]) == Decimal("0.8916116033")
    assert await pending_ids(client) == [deal["id"]]

    resolved = await resolve(client, deal["id"], accept=True)

    assert resolved.status_code == 200
    assert resolved.json()["status"] == "accepted"
    assert await pending_ids(client) == []
    rows = await report(client)
    assert Decimal(rows["USD"]["received_amount"]) == Decimal("100.00")
    assert Decimal(rows["EUR"]["paid_out_amount"]) == Decimal("89.16")
    assert rows["USD"]["deals_count"] == rows["EUR"]["deals_count"] == 1


@pytest.mark.usefixtures("rates")
async def test_declined_deal_is_neither_pending_nor_in_report(client: AsyncClient) -> None:
    deal_id = await create_deal(client)

    resolved = await resolve(client, deal_id, accept=False)

    assert resolved.json()["status"] == "declined"
    assert await pending_ids(client) == []
    assert await report(client) == {}


@pytest.mark.usefixtures("rates")
async def test_resolving_twice_returns_409(client: AsyncClient) -> None:
    deal_id = await create_deal(client)
    await resolve(client, deal_id, accept=True)

    response = await resolve(client, deal_id, accept=False)

    assert response.status_code == 409
    assert "already" in response.json()["detail"]


async def test_resolving_unknown_deal_returns_404(client: AsyncClient) -> None:
    response = await resolve(client, str(uuid4()), accept=True)

    assert response.status_code == 404


async def test_creating_deal_without_rates_returns_503(client: AsyncClient) -> None:
    response = await client.post(DEALS, json=USD_TO_EUR)

    assert response.status_code == 503


@pytest.mark.usefixtures("rates")
@pytest.mark.parametrize(
    "body",
    [
        {**USD_TO_EUR, "to_currency": "JPY"},
        {**USD_TO_EUR, "to_currency": "USD"},
        {**USD_TO_EUR, "from_currency": "usd"},
        {**USD_TO_EUR, "amount": "-5"},
        {**USD_TO_EUR, "amount": "1.005"},
        {"amount": "100.00", "from_currency": "USD"},
    ],
    ids=["unsupported", "same-currency", "lowercase", "negative", "3-decimals", "missing-field"],
)
async def test_invalid_deal_returns_422(client: AsyncClient, body: dict[str, str]) -> None:
    response = await client.post(DEALS, json=body)

    assert response.status_code == 422
    assert await pending_ids(client) == []


async def test_report_with_inverted_period_returns_422(client: AsyncClient) -> None:
    response = await client.get(REPORT, params={"date_from": "2026-10-20", "date_to": "2026-10-19"})

    assert response.status_code == 422
