from datetime import UTC, datetime
from decimal import Decimal

import pytest

from marketprice.competition import review_campaigns
from marketprice.flexible import calculate_catalog

NOW = datetime(2026, 11, 4, 12, tzinfo=UTC)


def observation(**changes):
    return (
        {
            "sku": "A",
            "marketplace": "custom",
            "currency": "IRR",
            "product_reference": "EXACT-MODEL-VARIANT",
            "match_confirmed": "true",
            "available": "true",
            "offer_condition": "new",
            "our_condition": "new",
            "competitor_delivered_price": "190",
            "our_customer_delivery_charge": "15",
            "observed_at": "2026-11-04T11:00:00+00:00",
            "source_url": "https://example.com/offer",
        }
        | changes
    )


def result():
    return calculate_catalog(
        [{"sku": "A", "purchase_cost": 100, "current_price": 200}],
        currency="IRR",
        target_margin="20%",
        marketplace="custom",
        discounts=(Decimal(".1"),),
        omitted_costs_confirmed=True,
    )


def test_campaign_comparison_includes_customer_delivery_not_seller_shipping_expense():
    reviewed = review_campaigns(result(), [observation()], now=NOW)
    assert reviewed[0]["review"] == "ABOVE_OBSERVED_PRICE"
    assert reviewed[0]["delivered_price_gap"] == 5
    assert reviewed[0]["buy_box_prediction"] == "NOT_PREDICTED"
    assert (
        review_campaigns(result(), [observation(our_customer_delivery_charge="0")], now=NOW)[0]["review"]
        == "WITHIN_OBSERVED_PRICE"
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"match_confirmed": "false"},
        {"available": "false"},
        {"currency": "USD"},
        {"observed_at": "2026-11-01T11:00:00+00:00"},
        {"observed_at": "2026-11-05T11:00:00+00:00"},
        {"observed_at": "2026-11-04T11:00:00"},
        {"our_customer_delivery_charge": ""},
        {"competitor_delivered_price": "10%"},
        {"offer_condition": "used"},
        {"product_reference": ""},
        {"source_url": "https://name:secret@example.com/"},
    ],
)
def test_unusable_observations_do_not_create_strategy(changes):
    r = review_campaigns(result(), [observation(**changes)], now=NOW)[0]
    assert r["evidence_status"] == "REJECTED" and r["review"] == "ADD_COMPARABLE_OFFER"
    assert r["rejection_reasons"]


def test_missing_evidence_and_unconfirmed_costs_remain_visible():
    assert review_campaigns(result(), [], now=NOW)[0]["evidence_status"] == "MISSING"
    r = result()
    r["Campaign_Simulations"][0]["decision_ready"] = False
    assert review_campaigns(r, [observation()], now=NOW)[0]["review"] == "CONFIRM_COSTS_OR_MARGIN"
