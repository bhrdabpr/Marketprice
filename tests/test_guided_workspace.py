from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


def open_app():
    return AppTest.from_file(str(Path("app.py").resolve())).run()


@pytest.mark.parametrize("language", ["en", "fa"])
def test_home_opens_each_workflow_and_returns(language):
    app = open_app()
    app.radio(key="ui_language").set_value(language).run()
    assert app.radio(key="workspace__" + language).value == "Overview"
    assert not app.get("file_uploader")
    for key, section in [
        ("pricing", "Pricing (قیمت گذاری)"), ("campaigns", "Campaigns"),
        ("listings", "Listings"), ("actuals", "Actual profit (سود واقعی)"),
        ("costs", "Cost impact"), ("sales", "Sales map"), ("changes", "Changes"),
    ]:
        app.button(key="tool_" + key).click().run()
        assert app.radio(key="workspace__" + language).value == section
        assert not app.exception
        app.button(key="back_to_tools").click().run()
        assert app.radio(key="workspace__" + language).value == "Overview"
        assert not app.exception


def test_pricing_source_and_settings_survive_navigation_and_clear():
    app = open_app()
    source = ("synthetic.csv", b"sku,purchase_cost,current_price\nDEMO,100,200\n")
    app.session_state["pricing_source"] = source
    app.button(key="tool_pricing").click().run()
    app.text_input(key="target_margin").set_value("25%").run()
    app.text_input(key="campaign_discounts").set_value("5%; 10%").run()
    next(c for c in app.checkbox if c.key.startswith("confirm_")).check().run()
    next(c for c in app.checkbox if c.key.startswith("currency_confirm_")).check().run()
    next(b for b in app.button if b.label == "Validate and calculate").click().run()
    before = app.session_state["result"]
    app.button(key="back_to_tools").click().run()
    app.button(key="tool_campaigns").click().run()
    assert not app.exception
    assert app.session_state["pricing_source"] == source
    assert app.text_input(key="target_margin").value == "25%"
    assert app.text_input(key="campaign_discounts").value == "5%; 10%"
    assert app.session_state["result"] == before
    assert any(d.proto.label == "Download campaign review" for d in app.get("download_button"))
    app.text_input(key="campaign_discounts").set_value("20%").run()
    assert "result" not in app.session_state
    assert not any(d.proto.label == "Download campaign review" for d in app.get("download_button"))
    app.button(key="clear_session").click().run()
    assert "pricing_source" not in app.session_state
    assert not app.exception


def test_market_change_invalidates_listing_download():
    app = open_app()
    app.button(key="tool_listings").click().run()
    app.checkbox(key="listing_demo_0").check().run()
    app.button(key="listing_run").click().run()
    assert app.session_state["listing_result"][1]["Sources"][0]["marketplace"] == "amazon.com"
    app.selectbox(key="listing_marketplace").set_value("amazon.ae").run()
    assert not any(d.proto.label == "Download listing review workbook" for d in app.get("download_button"))
    app.button(key="listing_run").click().run()
    assert app.session_state["listing_result"][1]["Sources"][0]["marketplace"] == "amazon.ae"
    assert not app.exception
