import csv
from copy import deepcopy
from datetime import date
from decimal import Decimal as D
from decimal import localcontext
from io import StringIO

import pytest

from marketprice.approvals import snapshot
from marketprice.flexible import calculate_catalog
from marketprice.presentation import display_value
from marketprice.replacement import campaign_requirement, quote_template, review_replacement

TODAY = date(2026, 11, 4)


def source(**settings):
    return calculate_catalog(
        [{"sku": "DEMO", "purchase_cost": 100, "current_price": 200}],
        **{
            "currency": "IRR",
            "marketplace": "custom",
            "target_margin": "20%",
            "omitted_costs_confirmed": True,
            "discounts": (D(".1"),),
            **settings,
        },
    )


def quote(result, **changes):
    row = next(csv.DictReader(StringIO(quote_template(result).decode("utf-8-sig"))))
    return {
        **row,
        "replacement_net_unit_cost": "140",
        "quoted_on": "2026-11-01",
        "valid_until": "2026-11-05",
        "source_reference": "SYNTHETIC-QUOTE",
        **changes,
    }


def test_independent_replenishment_floor_and_campaign_with_no_mutation():
    result = source()
    before = deepcopy(result)
    r = review_replacement(result, [quote(result)], as_of=TODAY)
    current, campaign = r["Replacement_Review"]
    assert not r["Quote_Errors"]
    assert current["historical_contribution"] == 100
    assert current["replacement_contribution"] == 60  # 200 - 140
    assert current["replacement_margin_floor"] == 175  # 140 / .8
    assert campaign["replacement_contribution"] == 40  # 180 - 140
    assert not current["decision_ready"] and not campaign["decision_ready"]
    assert result == before
    plan = campaign_requirement(
        baseline_profit=D(100), scenario_profit=D(40), baseline_units=10, extra_spend=D(60)
    )
    assert plan["required_units"] == 27  # ceil((10*100 + 60) / 40)
    assert plan["contribution_at_baseline_volume"] == 340
    assert plan["required_sales_multiplier"] == D("2.7")


@pytest.mark.parametrize(
    "market,currency", [("custom", "IRR"), ("digikala", "TOMAN"), ("amazon", "USD"), ("ebay", "GBP")]
)
def test_same_core_for_separate_markets_and_currencies(market, currency):
    result = source(marketplace=market, currency=currency)
    rows = review_replacement(result, [quote(result)], as_of=TODAY)["Replacement_Review"]
    assert rows[0]["replacement_margin_floor"] == 175
    assert rows[0]["marketplace"] == market and rows[0]["currency"] == currency


@pytest.mark.parametrize(
    "changes",
    [
        {"source_snapshot": "0" * 64},
        {"sku": "OTHER"},
        {"marketplace": "ebay"},
        {"currency": "TOMAN"},
        {"quoted_on": "2026-11-05"},
        {"valid_until": "2026-11-03"},
        {"replacement_net_unit_cost": "NaN"},
        {"replacement_net_unit_cost": "-1"},
        {"replacement_net_unit_cost": "20%"},
        {"replacement_net_unit_cost": ""},
        {"source_reference": " "},
        {"row": True},
        {"unknown_fee": 50},
    ],
)
def test_unusable_quotes_never_produce_scenarios(changes):
    result = source()
    reviewed = review_replacement(result, [quote(result, **changes)], as_of=TODAY)
    assert reviewed["Quote_Errors"]
    assert all("replacement_contribution" not in r for r in reviewed["Replacement_Review"])


def test_duplicates_and_rejected_companion_quote_block_affected_row():
    result = source()
    for extra in [quote(result), quote(result, valid_until="2026-11-02")]:
        reviewed = review_replacement(result, [quote(result), extra], as_of=TODAY)
        assert reviewed["Quote_Errors"]
        assert reviewed["Replacement_Review"][0]["replacement_review"] == "FIX_QUOTE"


def test_changed_calculation_rejects_old_quote_and_missing_stays_visible():
    result = source()
    old = quote(result)
    result["Assumptions"].append({"setting": "changed input", "value": True})
    assert snapshot(result) != old["source_snapshot"]
    reviewed = review_replacement(result, [old], as_of=TODAY)
    assert reviewed["Quote_Errors"]
    assert (
        review_replacement(result, [], as_of=TODAY)["Replacement_Review"][0]["replacement_review"]
        == "ADD_QUOTE"
    )


def test_provisional_costs_and_constraint_conflict_do_not_become_approval():
    result = source(omitted_costs_confirmed=False)
    reviewed = review_replacement(result, [quote(result)], as_of=TODAY)
    assert reviewed["Replacement_Review"][0]["replacement_review"] == "CONFIRM_COSTS"
    result = calculate_catalog(
        [{"sku": "DEMO", "purchase_cost": 100, "current_price": 140, "price_ceiling": 150}],
        currency="IRR",
        target_margin="20%",
        omitted_costs_confirmed=True,
    )
    row = review_replacement(result, [quote(result)], as_of=TODAY)["Replacement_Review"][0]
    assert row["replacement_constraint"] == "PRICE_CONSTRAINT_CONFLICT"
    assert not row["decision_ready"]


def test_floor_only_and_credit_not_subtracted_twice():
    result = calculate_catalog(
        [{"sku": "DEMO", "purchase_cost": 100, "input_tax_credit": 10}],
        currency="IRR",
        target_margin="20%",
        omitted_costs_confirmed=True,
    )
    row = review_replacement(result, [quote(result, replacement_net_unit_cost="120")], as_of=TODAY)[
        "Replacement_Review"
    ][0]
    assert row["historical_net_unit_cost"] == 90
    assert row["replacement_margin_floor"] == 150
    assert row["replacement_contribution"] is None and row["scenario_price"] is None
    assert row["replacement_review"] == "FLOOR_ONLY"


def test_currency_display_keeps_floor_money_and_units_are_not_converted():
    assert (
        display_value("replacement_margin_floor", D(1750), currency="IRR", display_currency="TOMAN") == "175"
    )
    assert display_value("required_units", 27, currency="IRR", display_currency="TOMAN") == "27"
    assert display_value("target_margin", D(".2"), currency="IRR", display_currency="TOMAN") == "20.00%"


def test_disconnected_and_caller_precision_independent(monkeypatch):
    import socket

    def blocked(*args, **kwargs):
        raise AssertionError("Financial review must not access the network")

    monkeypatch.setattr(socket, "socket", blocked)
    result = source()
    with localcontext() as ctx:
        ctx.prec = 6
        assert (
            review_replacement(result, [quote(result)], as_of=TODAY)["Replacement_Review"][0][
                "replacement_margin_floor"
            ]
            == 175
        )


@pytest.mark.parametrize("baseline,scenario", [(0, 40), (-1, 40), (100, 0), (100, -1)])
def test_campaign_nonpositive_comparison_is_not_a_sales_target(baseline, scenario):
    r = campaign_requirement(
        baseline_profit=D(baseline), scenario_profit=D(scenario), baseline_units=10, extra_spend=D(0)
    )
    assert r["required_units"] is None and r["status"] == "NO_POSITIVE_COMPARISON"


@pytest.mark.parametrize(
    "change",
    [{"extra_spend": D(-1)}, {"baseline_units": True}, {"baseline_units": 0}, {"scenario_profit": D("NaN")}],
)
def test_bad_budget_inputs(change):
    with pytest.raises(ValueError):
        campaign_requirement(
            **{
                "baseline_profit": D(100),
                "scenario_profit": D(40),
                "baseline_units": 10,
                "extra_spend": D(0),
                **change,
            }
        )


def test_quote_failure_isolated_and_currency_never_crossed():
    result = calculate_catalog(
        [
            {"sku": "A", "purchase_cost": 100, "current_price": 200, "currency": "IRR"},
            {"sku": "B", "purchase_cost": 100, "current_price": 200, "currency": "USD"},
            {"sku": "C", "purchase_cost": "", "current_price": 200, "currency": "IRR"},
        ],
        currency="IRR",
        target_margin="20%",
        omitted_costs_confirmed=True,
    )
    entries = list(csv.DictReader(StringIO(quote_template(result).decode("utf-8-sig"))))
    quotes = [
        {
            **r,
            "replacement_net_unit_cost": "140",
            "quoted_on": "2026-11-01",
            "valid_until": "2026-11-05",
            "source_reference": "synthetic",
        }
        for r in entries
    ]
    quotes[0]["currency"] = "USD"
    review = review_replacement(result, quotes, as_of=TODAY)
    current = [r for r in review["Replacement_Review"] if r.get("scenario", "CURRENT") == "CURRENT"]
    assert current[0]["replacement_review"] == "FIX_QUOTE"
    assert current[1]["replacement_contribution"] == 60
    assert current[1]["currency"] == "USD"
    assert current[2]["replacement_review"] == "FIX_PRODUCT"


def test_quote_template_escapes_formula_like_skus_without_losing_identity():
    result = calculate_catalog(
        [{"sku": "=DEMO", "purchase_cost": 100, "current_price": 200}],
        currency="IRR",
        target_margin="20%",
        omitted_costs_confirmed=True,
    )
    q = quote(result)
    assert q["sku"] == "'=DEMO"
    review = review_replacement(result, [q], as_of=TODAY)
    assert not review["Quote_Errors"]
    assert review["Replacement_Review"][0]["sku"] == "=DEMO"
