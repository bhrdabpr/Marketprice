import csv
from io import StringIO
from pathlib import Path

import pytest
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


def test_campaign_exposes_required_sales_without_predicting_demand():
    from decimal import Decimal

    result = calculate_catalog(
        [{"sku": "DEMO", "purchase_cost": 100, "current_price": 200}],
        currency="USD",
        target_margin="20%",
        discounts=(Decimal(".1"), Decimal(".5"), Decimal(".6")),
        omitted_costs_confirmed=True,
    )
    offers = result["Campaign_Simulations"]
    # Independently: baseline contribution=100; 10% off =>180-100=80.
    assert offers[0]["baseline_unit_profit"] == 100
    assert offers[0]["profit"] == 80
    assert offers[0]["required_sales_multiplier"] == Decimal("1.25")
    assert offers[1]["required_sales_multiplier"] is None  # zero contribution
    assert offers[2]["required_sales_multiplier"] is None  # loss
    assert "not a sales forecast" in offers[0]["volume_note"].lower()
    from io import BytesIO

    from openpyxl import load_workbook

    from marketprice.io import workbook_bytes

    book = load_workbook(BytesIO(workbook_bytes(result)), read_only=True, data_only=True)
    rows = list(book["Campaign_Simulations"].values)
    exported = dict(zip(rows[0], rows[1]))
    assert exported["required_sales_multiplier"] == 1.25
    assert exported["baseline_unit_profit"] == 100
    book.close()


def test_publication_guard_blocks_sensitive_artifacts_without_printing_contents():
    from scripts.check_publication import violations

    assert violations("private/customer.csv", b"example")
    assert violations("samples/customer.xlsx", b"example")
    assert violations(".env", b"example")
    assert violations("docs/screenshot-final-en.png", b"example")
    assert violations("notes.txt", b"ghp_" + b"x" * 36)
    assert not violations("samples/demo.csv", b"sku,purchase_cost\nDEMO,100")


@pytest.mark.parametrize("language", ["en", "fa"])
def test_clear_preserves_display_preferences_and_clears_both_workspaces(language):
    app = AppTest.from_file(Path("app.py").resolve()).run()
    app.radio(key="ui_language").set_value(language).run()
    app.selectbox(key="display_currency__" + language).select("TOMAN").run()
    app.checkbox(key="digits_" + language).set_value(True).run()
    app.text_input(key="target_margin").set_value("42%").run()
    for key in ("result", "download", "summary_download", "import_rows", "import_key",
                "operations_result", "operations_input", "fingerprint", "delay_days"):
        app.session_state[key] = "synthetic private data"
    app.button(key="clear_session").click().run()
    assert not app.exception
    assert app.radio(key="ui_language").value == language
    assert app.selectbox(key="display_currency__" + language).value == "TOMAN"
    assert app.checkbox(key="digits_" + language).value is True
    assert app.text_input(key="target_margin").value == "10%"
    assert app.button(key="clear_session").label == (
        "پاک‌کردن اطلاعات این نشست" if language == "fa" else "Clear session data")
    for key in ("result", "download", "summary_download", "import_rows", "import_key",
                "operations_result", "operations_input", "fingerprint", "delay_days"):
        assert key not in app.session_state
    app.button(key="clear_session").click().run()
    assert app.radio(key="ui_language").value == language
    assert not app.exception
