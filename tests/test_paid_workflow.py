import csv
from io import StringIO
from pathlib import Path

from streamlit.testing.v1 import AppTest

from marketprice.flexible import calculate_catalog
from marketprice.io import pricing_summary_csv
from marketprice.templates import load_setup, save_setup


def test_saved_setup_retains_margin_and_promotion_choices():
    settings = {
        "currency": "IRR",
        "target_margin": "12%",
        "extra_margins": "18%; 25%",
        "campaign_discounts": "7%",
        "discount_kind": "percent",
        "platform_share": "20%",
    }
    payload = save_setup(["purchase_cost"], {"purchase_cost": "purchase_cost"}, {}, settings)
    assert load_setup(payload, ["purchase_cost"])["settings"] == settings


def test_summary_keeps_invalid_rows_and_exact_amounts_without_original_columns():
    result = calculate_catalog(
        [
            {"sku": "=DEMO", "purchase_cost": 100, "current_price": 200, "commission_rate": "0%"},
            {"sku": "BAD", "purchase_cost": 100, "current_price": 200, "commission_rate": ""},
        ],
        currency="IRR",
        target_margin="20%",
        omitted_costs_confirmed=True,
    )
    result["Product_Calculations"][0]["original_secret"] = "do not export"
    payload = pricing_summary_csv(result)
    rows = list(csv.DictReader(StringIO(payload.decode("utf-8-sig"))))
    assert rows[0]["sku"] == "'=DEMO"
    assert rows[0]["current_price"] == "200"
    assert rows[0]["profit"] == "100"
    assert rows[1]["status"] == "INVALID" and "commission_rate" in rows[1]["problem_fields"]
    assert b"do not export" not in payload
    assert result["Product_Calculations"][0]["sku"] == "=DEMO"


def test_clear_session_removes_financial_settings_and_cached_results():
    app = AppTest.from_file(Path("app.py").resolve()).run()
    app.text_input(key="target_margin").set_value("42%").run()
    app.session_state["result"] = {"private": "example"}
    app.session_state["download"] = b"example"
    app.button(key="clear_session").click().run()
    assert not app.exception
    assert app.text_input(key="target_margin").value == "10%"
    assert "result" not in app.session_state and "download" not in app.session_state
