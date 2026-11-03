from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from marketprice.actuals import reconcile
from marketprice.approvals import approved_changes, snapshot
from marketprice.config import load_profiles
from marketprice.contracts import load_contract
from marketprice.excel_bridge import calculate_matrix, result_matrix
from marketprice.flexible import calculate_catalog
from marketprice.io import read_upload
from marketprice.templates import load_setup, save_setup

AS_OF = date(2026, 11, 1)


def sale(**changes):
    return {
        "transaction_id": "S1",
        "marketplace": "market",
        "currency": "IRR",
        "date": "2026-10-01",
        "kind": "sale",
        "amount": "2000",
        "order_id": "O1",
        "sku": "A",
        "settlement_id": "P1",
        "quantity": "2",
    } | changes


def cost(**changes):
    return {
        "sku": "A",
        "currency": "IRR",
        "effective_date": "2026-09-01",
        "historical_unit_cost": "500",
        "replacement_unit_cost": "600",
        "source": "Invoice 1",
    } | changes


def test_cost_confidence_distinguishes_absent_estimated_and_confirmed_zero():
    rows = [{"purchase_cost": 100, "current_price": 200, "commission_rate": 0}]
    provisional = calculate_catalog(rows, currency="IRR", target_margin="20%")
    assert provisional["Price_Analysis"][0]["action"] == "CONFIRM_COSTS"
    assert not provisional["Price_Recommendations"][0]["decision_ready"]
    assert "shipping" in provisional["Cost_Confidence"][0]["missing_costs"]
    assert "commission_rate" in provisional["Cost_Confidence"][0]["confirmed_zero_costs"]
    confirmed = calculate_catalog(rows, currency="IRR", target_margin="20%", omitted_costs_confirmed=True)
    decision = confirmed["Price_Analysis"][0]
    assert decision["margin_floor"] == 125 and decision["normal_price"] == 200
    assert decision["profit"] == 100 and decision["action"] == "KEEP"
    estimated = calculate_catalog(
        rows,
        currency="IRR",
        target_margin="20%",
        omitted_costs_confirmed=True,
        cost_states={"purchase_cost": "estimated"},
    )
    assert estimated["Cost_Confidence"][0]["cost_confidence"] == "ESTIMATED"
    assert not estimated["Price_Analysis"][0]["decision_ready"]


def test_blank_commission_invalidates_only_product_even_after_confirmation():
    result = calculate_catalog(
        [{"purchase_cost": 100, "commission_rate": "10%"}, {"purchase_cost": 100, "commission_rate": None}],
        currency="IRR",
        target_margin="10%",
        omitted_costs_confirmed=True,
    )
    assert [r["status"] for r in result["Product_Calculations"]] == ["VALID", "INVALID"]
    assert result["Action_List"][0]["action"] == "FIX_PRODUCT"


def test_saved_mapping_round_trip_and_template_drift_rejected():
    headers = ["خرید", "کمیسیون"]
    payload = save_setup(
        headers,
        {"خرید": "purchase_cost", "کمیسیون": "commission_rate"},
        {"کمیسیون": "Percentage number"},
        {"currency": "IRR", "target_margin": "10%"},
    )
    assert load_setup(payload, headers[::-1])["version"] == 1
    with pytest.raises(ValueError, match="Template changed"):
        load_setup(payload, headers + ["shipping"])
    with pytest.raises(ValueError, match="Duplicate"):
        save_setup(headers, dict.fromkeys(headers, "purchase_cost"), {}, {})


def test_excel_bridge_reuses_engine_and_preserves_zero_blanks_and_literal_text():
    matrix = [["sku", "purchase_cost", "commission_rate"], ["=cmd", 100, 0], ["B", 100, None]]
    setup = save_setup(
        matrix[0],
        dict(zip(matrix[0], matrix[0])),
        {},
        {"currency": "IRR", "target_margin": "20%", "omitted_costs_confirmed": True},
    )
    result = calculate_matrix(matrix, setup)
    assert [r["status"] for r in result["Product_Calculations"]] == ["VALID", "INVALID"]
    assert result["Price_Analysis"][0]["normal_price"] == 125
    values = result_matrix(result)
    assert any("'=cmd" in r for r in values)
    assert len({len(r) for r in values}) == 1
    assert matrix[1][0] == "=cmd"


def test_settlement_transfer_not_revenue_and_dated_costs_change_replacement_only():
    entries = [
        sale(),
        sale(transaction_id="F1", kind="fee", amount="-200", quantity=0, expected_amount="-180"),
        sale(transaction_id="P1", kind="payout", amount="1800", quantity=0, order_id="", sku=""),
    ]
    result = reconcile(
        entries,
        [cost(), cost(effective_date="2026-10-15", historical_unit_cost=650, replacement_unit_cost=700)],
        as_of=AS_OF,
    )
    row = result["Order_Contribution"][0]
    assert row["historical_cost"] == 1000
    assert row["contribution"] == 800
    assert row["replacement_contribution"] == 400
    assert result["Settlement_Reconciliation"][0]["status"] == "MATCHED"
    assert result["Platform_Comparison"][0]["contribution"] == 800
    assert any(a["action"] == "EXPECTED_AMOUNT_DIFFERS" and a["impact"] == 20 for a in result["Action_List"])
    assert row["cost_sources"][0]["historical_cost_row"] == 2


def test_refund_does_not_automatically_restore_cogs_and_reserve_not_expense():
    entries = [
        sale(),
        sale(transaction_id="R1", kind="refund", amount=-2000, quantity=0),
        sale(transaction_id="H1", kind="reserve", amount=-100, quantity=0),
    ]
    result = reconcile(entries, [cost()], as_of=AS_OF)
    assert result["Order_Contribution"][0]["contribution"] == -1000
    assert result["Settlement_Reconciliation"][0]["expected_payout"] == -100
    entries.append(sale(transaction_id="C1", kind="cost_recovery", amount=1000, quantity=0))
    result = reconcile(entries, [cost()], as_of=AS_OF)
    assert result["Order_Contribution"][0]["contribution"] == 0
    assert result["Settlement_Reconciliation"][0]["expected_payout"] == -100


def test_unknown_cost_and_orphan_transactions_remain_unresolved():
    result = reconcile(
        [sale(), sale(transaction_id="R1", order_id="MISSING", kind="refund", amount=-10, quantity=0)],
        [],
        as_of=AS_OF,
    )
    assert all(r["contribution"] is None for r in result["Order_Contribution"])
    assert result["Platform_Comparison"][0]["contribution"] is None
    assert {"MISSING_DATED_COST", "ORDER_SALE_MISSING"} <= {r["action"] for r in result["Action_List"]}


def test_duplicate_transactions_are_all_excluded_and_never_balanced_away():
    result = reconcile(
        [sale(), sale(), sale(transaction_id="P1", kind="payout", amount=2000, quantity=0)],
        [cost()],
        as_of=AS_OF,
    )
    assert len(result["Errors"]) == 2
    assert result["Settlement_Reconciliation"][0]["status"] == "REVIEW"
    assert result["Settlement_Reconciliation"][0]["difference"] == 2000


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": True},
        {"amount": "2%"},
        {"amount": "NaN"},
        {"kind": "fee", "amount": 20, "quantity": 0},
        {"date": "2026-12-01"},
        {"currency": "UNKNOWN"},
        {"quantity": 0},
    ],
)
def test_invalid_transaction_does_not_make_profit(changes):
    result = reconcile([sale(**changes)], [cost()], as_of=AS_OF)
    assert result["Errors"] and not result["Order_Contribution"]


def test_duplicate_costs_do_not_fall_back_to_older_valid_cost():
    result = reconcile([sale()], [cost(), cost(), cost(effective_date="2026-08-01")], as_of=AS_OF)
    assert len(result["Errors"]) == 2
    assert result["Order_Contribution"][0]["contribution"] is None


def test_campaign_unallocated_fees_visible_and_currency_totals_separate():
    entries = [
        sale(campaign="Yalda", phase="during"),
        sale(transaction_id="F1", kind="fee", amount=-100, quantity=0),
        sale(transaction_id="USD1", currency="USD", amount=20),
    ]
    result = reconcile(
        entries, [cost(), cost(currency="USD", historical_unit_cost=3, replacement_unit_cost=4)], as_of=AS_OF
    )
    assert len(result["Platform_Comparison"]) == 2
    assert result["Campaign_Actuals"] == []
    assert any(r["action"] == "AMBIGUOUS_CAMPAIGN_ALLOCATION" for r in result["Action_List"])


def test_synthetic_samples_reconcile_to_known_results():
    folder = Path("samples/operations")
    inputs = [
        read_upload((folder / name).read_bytes(), name, preserve_headers=True)
        for name in ["transactions.csv", "costs.csv"]
    ]
    result = reconcile(*inputs, as_of=AS_OF)
    assert not result["Errors"]
    assert [r["contribution"] for r in result["Platform_Comparison"]] == [800, 850]
    assert [r["difference"] for r in result["Settlement_Reconciliation"]] == [0, -50]
    assert len(result["Campaign_Actuals"]) == 2
    assert [r["contribution_per_sold_unit"] for r in result["Product_Platform"]] == [400, 850]
    assert [r["days_first_sale_to_last_payout"] for r in result["Settlement_Reconciliation"]] == [9, 10]


def test_approval_requires_costs_contract_and_unchanged_snapshot():
    result = calculate_catalog(
        [{"purchase_cost": 100, "current_price": 110}],
        currency="IRR",
        target_margin="20%",
        omitted_costs_confirmed=True,
    )
    key = (2, "0.2")
    token = snapshot(result)
    with pytest.raises(ValueError, match="fee rules"):
        approved_changes(result, [key], expected_snapshot=token)
    approved = approved_changes(result, [key], expected_snapshot=token, fee_rules_confirmed=True)
    assert approved[0]["approved_price"] == 125 and approved[0]["publication_status"] == "NOT_PUBLISHED"
    result["Price_Analysis"][0]["normal_price"] = D(126)
    with pytest.raises(ValueError, match="stale"):
        approved_changes(result, [key], expected_snapshot=token, fee_rules_confirmed=True)


def test_campaign_multiplier_is_required_volume_not_prediction():
    result = calculate_catalog(
        [{"purchase_cost": 100, "current_price": 200}],
        currency="IRR",
        target_margin="20%",
        omitted_costs_confirmed=True,
        events=(("test", D(".2"), D(0)),),
    )
    offer = result["Seasonal_Campaigns"][0]
    assert offer["campaign_price"] == 125
    assert offer["required_sales_multiplier"] == 4


def test_dated_contract_expiry_currency_and_unsupported_terms():
    import json

    profile = load_profiles()["generic"].model_dump(mode="json")
    profile["effective_date"] = "2026-01-01"
    data = {
        "seller_reference": "demo",
        "currency": "IRR",
        "valid_from": "2026-01-01",
        "valid_until": "2026-12-31",
        "reviewed_on": "2026-10-01",
        "reviewed_by": "seller",
        "evidence_reference": "Synthetic contract",
        "profile": profile,
    }
    assert load_contract(json.dumps(data).encode(), as_of=AS_OF, currency="IRR")[0].seller_reference == "demo"
    with pytest.raises(ValueError, match="currency"):
        load_contract(json.dumps(data).encode(), as_of=AS_OF, currency="USD")
    with pytest.raises(ValueError, match="expired"):
        load_contract(json.dumps(data).encode(), as_of=date(2027, 1, 1), currency="IRR")
    data["profile"]["unsupported_fee_cap"] = 100
    with pytest.raises(ValueError):
        load_contract(json.dumps(data).encode(), as_of=AS_OF, currency="IRR")


def test_saved_estimates_are_not_upgraded_to_confirmed_and_absent_estimates_are_missing():
    setup = save_setup(
        ["purchase_cost"],
        {"purchase_cost": "purchase_cost"},
        {},
        {
            "currency": "IRR",
            "target_margin": "20%",
            "omitted_costs_confirmed": True,
            "cost_states": {"purchase_cost": "estimated"},
        },
    )
    result = calculate_matrix([["purchase_cost"], [100]], setup)
    assert not result["Price_Analysis"][0]["decision_ready"]
    result = calculate_catalog(
        [{"purchase_cost": 100}],
        currency="IRR",
        target_margin="20%",
        omitted_costs_confirmed=True,
        cost_states={"shipping": "estimated"},
    )
    assert "shipping" in result["Cost_Confidence"][0]["missing_costs"]


def test_excel_native_date_values_and_refund_sku_mismatch():
    from datetime import datetime

    result = reconcile([sale()], [cost(effective_date=datetime(2026, 9, 1))], as_of=AS_OF)
    assert not result["Errors"] and result["Order_Contribution"][0]["contribution"] == 1000
    result = reconcile(
        [sale(), sale(transaction_id="R1", kind="refund", amount=-10, quantity=0, sku="OTHER")],
        [cost()],
        as_of=AS_OF,
    )
    assert result["Order_Contribution"][0]["contribution"] is None
    assert any(r["action"] == "ORDER_SKU_MISMATCH" for r in result["Action_List"])
