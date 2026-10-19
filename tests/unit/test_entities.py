import dataclasses
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.entities import Deal
from app.domain.exceptions import DealAlreadyResolvedError, SameCurrencyExchangeError
from app.domain.value_objects import CurrencyCode, DealStatus, ExchangeRate

RATE_DATE = date(2026, 10, 17)
CREATED_AT = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
RESOLVED_AT = datetime(2026, 10, 17, 12, 5, tzinfo=UTC)

USD_RATE = ExchangeRate(RATE_DATE, CurrencyCode("USD"), 1, Decimal("3.0091"))
EUR_RATE = ExchangeRate(RATE_DATE, CurrencyCode("EUR"), 1, Decimal("3.3749"))


def make_deal() -> Deal:
    """A pending deal: 100 USD -> EUR"""
    return Deal.create(Decimal(100), USD_RATE, EUR_RATE, CREATED_AT)


def test_create_builds_pending_deal_from_rates() -> None:
    deal = make_deal()

    assert deal.status is DealStatus.PENDING
    assert deal.amount == Decimal(100)
    assert deal.from_currency == CurrencyCode("USD")
    assert deal.to_currency == CurrencyCode("EUR")
    assert deal.rate == Decimal("0.8916116033")
    assert deal.converted_amount == Decimal("89.16")
    assert deal.created_at == CREATED_AT
    assert deal.resolved_at is None


def test_create_assigns_unique_id() -> None:
    assert make_deal().id != make_deal().id


def test_create_propagates_conversion_errors() -> None:
    with pytest.raises(SameCurrencyExchangeError):
        Deal.create(Decimal(100), USD_RATE, USD_RATE, CREATED_AT)


@pytest.mark.parametrize(
    ("resolve", "expected_status"),
    [(Deal.accept, DealStatus.ACCEPTED), (Deal.decline, DealStatus.DECLINED)],
    ids=["accept", "decline"],
)
def test_resolving_pending_deal_sets_status_and_time(
    resolve: Callable[[Deal, datetime], None], expected_status: DealStatus
) -> None:
    deal = make_deal()
    resolve(deal, RESOLVED_AT)

    assert deal.status is expected_status
    assert deal.resolved_at == RESOLVED_AT


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (Deal.accept, Deal.accept),
        (Deal.accept, Deal.decline),
        (Deal.decline, Deal.accept),
        (Deal.decline, Deal.decline),
    ],
    ids=["accept-twice", "decline-after-accept", "accept-after-decline", "decline-twice"],
)
def test_resolved_deal_cannot_be_resolved_again(
    first: Callable[[Deal, datetime], None], second: Callable[[Deal, datetime], None]
) -> None:
    deal = make_deal()
    first(deal, RESOLVED_AT)
    status_before = deal.status

    with pytest.raises(DealAlreadyResolvedError):
        second(deal, datetime(2026, 10, 17, 13, 0, tzinfo=UTC))

    assert deal.status is status_before
    assert deal.resolved_at == RESOLVED_AT


def test_deal_keeps_identity_after_state_change() -> None:
    deal = make_deal()
    snapshot = dataclasses.replace(deal)
    deal.accept(RESOLVED_AT)

    assert deal == snapshot
    assert hash(deal) == hash(snapshot)


def test_deals_with_same_fields_but_different_id_are_not_equal() -> None:
    assert make_deal() != make_deal()


def test_deal_is_not_equal_to_other_types() -> None:
    deal = make_deal()

    assert deal != deal.id
