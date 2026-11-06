"""Exercise app actions and post-action state with synthetic uploads in both languages."""

from io import BytesIO
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from marketprice.i18n import translate
from marketprice.templates import save_setup


class Upload(BytesIO):
    def __init__(self, data, name):
        super().__init__(data)
        self.name = name


@pytest.mark.parametrize("language", ["en", "fa"])
def test_pricing_actions_and_invalidation(monkeypatch, language):
    uploads = {
        "catalog_upload": Upload(b"sku,purchase_cost,current_price\nDEMO,100,200\nBAD,,200\n", "demo.csv")
    }
    monkeypatch.setattr(
        st, "file_uploader", lambda *args, key=None, **kw: uploads.get(key.split("__session_")[0])
    )
    app = AppTest.from_file(Path("app.py").resolve()).run()
    app.radio(key="ui_language").set_value(language).run()
    t = lambda text: translate(text, language)

    def button(text):
        return next(b for b in app.button if b.label == t(text))

    def download(text):
        assert any(d.proto.label == t(text) for d in app.get("download_button"))

    assert button("Validate and calculate").disabled
    next(c for c in app.checkbox if c.key.startswith("confirm_")).check().run()
    app.checkbox(key="omitted_").check().run()
    download("Save reusable setup (ذخیره تنظیمات)")
    button("Validate and calculate").click().run()
    assert not app.exception and not app.error
    result = app.session_state["result"]
    assert [r["status"] for r in result["Product_Calculations"]] == ["VALID", "INVALID"]
    app.button(key="prepare_summary").click().run()
    download("Download pricing summary CSV")
    app.button(key="prepare_report").click().run()
    download("Download results workbook")
    assert app.session_state["result"] == result
    app.number_input(key="delay_days").set_value(30).run()
    app.number_input(key="delay_rate").set_value(36.5).run()
    app.checkbox(key="delay_confirm").check().run()
    download("Download settlement scenario evidence")
    download("Download competitor evidence template")
    selection = next(m for m in app.multiselect if m.key.startswith("approve_"))
    selection.select(selection.options[0]).run()
    next(c for c in app.checkbox if c.key.startswith("fee_")).check().run()
    download("Download approved change manifest")
    app.radio(key="ui_language").set_value("en" if language == "fa" else "fa").run()
    assert app.session_state["result"] == result
    assert app.session_state["download"]
    app.text_input(key="target_margin").set_value("30%").run()
    assert "result" not in app.session_state
    assert "download" not in app.session_state
    assert "summary_download" not in app.session_state
    assert not app.exception and not app.error


def test_saved_setup_matches_visible_settings_and_allows_edits(monkeypatch):
    headers = ["sku", "purchase_cost", "current_price"]
    uploads = {
        "catalog_upload": Upload(b"sku,purchase_cost,current_price\nDEMO,100,200\n", "demo.csv"),
        "setup": Upload(
            save_setup(
                headers,
                dict(zip(headers, headers)),
                {},
                {
                    "currency": "TOMAN",
                    "target_margin": "22%",
                    "marketplace": "custom",
                    "extra_margins": "30%",
                    "campaign_discounts": "5%",
                    "omitted_costs_confirmed": True,
                },
            ),
            "setup.json",
        ),
    }
    monkeypatch.setattr(
        st, "file_uploader", lambda *args, key=None, **kw: uploads.get(key.split("__session_")[0])
    )
    app = AppTest.from_file(Path("app.py").resolve()).run()
    assert not app.exception and not app.error
    assert app.text_input(key="target_margin").value == "22%"
    assert app.selectbox(key="input_currency__en").value == "TOMAN"
    app.text_input(key="target_margin").set_value("25%").run()
    next(c for c in app.checkbox if c.key.startswith("confirm_")).check().run()
    next(b for b in app.button if b.label == "Validate and calculate").click().run()
    assert not app.exception and not app.error
    row = app.session_state["result"]["Price_Recommendations"][0]
    assert str(row["target_margin"]) == "0.25"
    assert row["currency"] == "TOMAN"


@pytest.mark.parametrize("language", ["en", "fa"])
def test_all_evidence_downloads_use_current_state_without_rerunning(monkeypatch, language):
    import json
    from datetime import UTC, datetime

    from openpyxl import load_workbook
    from streamlit.delta_generator import DeltaGenerator

    from tests.test_digikala import native_invoice

    downloads = {}
    original = DeltaGenerator.download_button

    def capture(self, label, data, file_name=None, *args, **kwargs):
        assert kwargs.get("on_click") == "ignore", file_name
        downloads[file_name] = data
        return original(self, label, data, file_name, *args, **kwargs)

    monkeypatch.setattr(DeltaGenerator, "download_button", capture)
    monkeypatch.setattr(st, "download_button", lambda *args, **kwargs: capture(st._main, *args, **kwargs))
    offers = (
        "sku,marketplace,currency,product_reference,match_confirmed,available,offer_condition,our_condition,competitor_delivered_price,our_customer_delivery_charge,observed_at,source_url\n"
        f"DEMO,custom,IRR,EXACT-DEMO,true,true,new,new,190,0,{datetime.now(UTC).isoformat()},https://example.com/demo\n"
    )
    uploads = {
        "catalog_upload": Upload(b"sku,purchase_cost,current_price\nDEMO,100,200\n", "demo.csv"),
        "competitor_evidence": Upload(offers.encode(), "offers.csv"),
    }
    monkeypatch.setattr(
        st, "file_uploader", lambda *args, key=None, **kw: uploads.get(key.split("__session_")[0])
    )
    app = AppTest.from_file(Path("app.py").resolve()).run()
    app.radio(key="ui_language").set_value(language).run()
    next(c for c in app.checkbox if c.key.startswith("confirm_")).check().run()
    app.checkbox(key="omitted_").check().run()
    next(b for b in app.button if b.label == translate("Validate and calculate", language)).click().run()
    app.number_input(key="delay_days").set_value(30).run()
    app.number_input(key="delay_rate").set_value(36.5).run()
    app.checkbox(key="delay_confirm").check().run()
    app.button(key="prepare_summary").click().run()
    app.button(key="prepare_report").click().run()
    select = next(m for m in app.multiselect if m.key.startswith("approve_"))
    select.select(select.options[0]).run()
    next(c for c in app.checkbox if c.key.startswith("fee_")).check().run()
    assert not app.exception and not app.error
    delay = json.loads(downloads["marketprice_settlement_scenario.json"])
    assert delay["review"][0]["additional_capital_cost"] == "3.000"
    assert float(delay["review"][0]["contribution_after_delay"]) == 97
    passport = json.loads(downloads["marketprice_campaign_passport.json"])
    assert passport["review"][0]["review"] == "WITHIN_OBSERVED_PRICE"
    assert passport["review"][0]["buy_box_prediction"] == "NOT_PREDICTED"
    assert json.loads(downloads["marketprice_approved.json"])
    assert downloads["competitor-evidence.csv"]
    assert downloads["sample_input.xlsx"]
    assert downloads["marketprice_summary.csv"]
    assert downloads["marketprice_results.xlsx"]
    assert downloads["marketprice_setup.json"]
    app.radio[1].set_value("Actual profit (سود واقعی)").run()
    assert next(
        b for b in app.button if b.label == translate("Analyze actual profit (تحلیل سود واقعی)", language)
    ).disabled
    uploads["digikala_invoice"] = Upload(native_invoice(), "digikala-invoice.xlsx")
    app.run()
    next(
        b for b in app.button if b.label == translate("Review Digikala invoice", language)
    ).click().run()
    assert app.session_state["digikala_invoice_result"]["Invoice_Reconciliation"][0]["status"] == "MATCHED"
    assert downloads["marketprice_digikala_invoice_review.xlsx"]
    assert downloads["marketprice_digikala_transactions.xlsx"]
    app.button(key="operations_demo_button").click().run()
    demo = app.session_state["operations_result"]
    assert [r["contribution"] for r in demo["Platform_Comparison"]] == [800, 850]
    assert downloads["transactions.csv"] and downloads["costs.csv"]
    uploads["transactions"] = Upload(
        Path("samples/operations/transactions.csv").read_bytes(), "transactions.csv"
    )
    uploads["costs"] = Upload(Path("samples/operations/costs.csv").read_bytes(), "costs.csv")
    app.run()
    assert "operations_result" not in app.session_state
    assert "digikala_invoice_result" in app.session_state
    app.checkbox(key="operations_confirmed").check().run()
    next(
        b for b in app.button if b.label == translate("Analyze actual profit (تحلیل سود واقعی)", language)
    ).click().run()
    assert not app.exception and not app.error
    book = load_workbook(BytesIO(downloads["marketprice_actuals.xlsx"]), read_only=True, data_only=True)
    assert len(list(book["Platform_Comparison"].values)) == 3
    book.close()
    app.button(key="clear_session").click().run()
    assert app.radio(key="ui_language").value == language
    assert app.session_state["session_epoch"] == 1
    assert "operations_result" not in app.session_state
    assert "digikala_invoice_result" not in app.session_state
