from copy import deepcopy
from decimal import Decimal as D

import pytest

from marketprice.flexible import calculate_catalog
from marketprice.presentation import display_value
from marketprice.settlement_scenarios import review_delay


def catalog(confirmed=True):
    return calculate_catalog(
        [
            {"sku": "DEMO", "purchase_cost": 1000, "current_price": 1200},
            {"sku": "MISSING", "purchase_cost": "", "current_price": 1200},
        ],
        currency="IRR",
        target_margin="10%",
        discounts=(D(".1"),),
        omitted_costs_confirmed=confirmed,
    )


def test_independent_current_and_campaign_comparison_and_no_mutation():
    source = catalog()
    before = deepcopy(source)
    rows = review_delay(source, annual_rate=D(".365"), extra_days=30)
    current, invalid, campaign = rows
    # 1000 * .365 * 30 /365 =30; 1200-1000=200; 1080-1000=80.
    assert current["additional_capital_cost"] == 30
    assert current["contribution_after_delay"] == 170
    assert campaign["contribution_after_delay"] == 50
    assert invalid["delay_review"] == "FIX_PRODUCT"
    assert not any(r["decision_ready"] for r in rows)
    assert source == before


def test_zero_delay_and_loss_remain_distinct_from_approval():
    assert review_delay(catalog(), annual_rate=D(0), extra_days=30)[0]["additional_capital_cost"] == 0
    rows = review_delay(catalog(), annual_rate=D(".365"), extra_days=200)
    assert rows[0]["delay_review"] == "BREAK_EVEN_AFTER_DELAY"
    assert rows[-1]["delay_review"] == "LOSS_AFTER_DELAY"
    assert (
        review_delay(catalog(False), annual_rate=D(".365"), extra_days=30)[0]["delay_review"]
        == "CONFIRM_COSTS"
    )


@pytest.mark.parametrize(
    "rate,days",
    [(D("NaN"), 30), (D("-.1"), 30), (D(11), 30), (D(1), -1), (D(1), True), (D(1), 3651), (D(1), 1.5)],
)
def test_invalid_assumptions(rate, days):
    with pytest.raises(ValueError):
        review_delay(catalog(), annual_rate=rate, extra_days=days)


def test_rial_toman_display_does_not_convert_rates_or_change_source():
    assert display_value("additional_capital_cost", D(30), currency="IRR", display_currency="TOMAN") == "3"
    assert display_value("annual_rate", D(".365"), currency="IRR", display_currency="TOMAN") == "36.50%"
    assert display_value("delay_review", "LOSS_AFTER_DELAY", language="fa") == "زیان پس از هزینه تأخیر"
