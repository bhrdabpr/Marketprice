from copy import deepcopy
from dataclasses import fields
from decimal import Decimal as D
from pathlib import Path

from streamlit.testing.v1 import AppTest

from marketprice.channels import CHANNELS, excluded_columns, matching_fields, scoped_mapping
from marketprice.config import load_profiles
from marketprice.engine import Ledger
from marketprice.flexible import calculate_catalog
from marketprice.i18n import translate
from marketprice.importing import IGNORE, map_rows, suggest_mapping
from marketprice.presentation import MONEY_FIELDS, display_value, filter_results, preview


def test_toman_rial_display_is_exact_and_does_not_convert_other_currencies_or_rates():
    assert display_value("current_price", D(12340), currency="IRR", display_currency="TOMAN") == "1,234"
    assert (
        display_value("current_price", D(112), currency="IRR", display_currency="TOMAN", persian_digits=True)
        == "۱۱٫۲"
    )
    assert display_value("profit", D("-12.5"), currency="TOMAN", display_currency="IRR") == "-125"
    assert display_value("profit", D(100), currency="USD", display_currency="TOMAN") == "100"
    assert display_value("target_margin", D(".1"), currency="IRR", display_currency="TOMAN") == "10.00%"
    assert display_value("margin_floor", D(1200), currency="IRR", display_currency="TOMAN") == "120"
    assert display_value("profit", D(0), currency="IRR", persian_digits=True) == "۰"
    assert display_value("sku", "000123", persian_digits=True) == "000123"
    assert {f.name for f in fields(Ledger)} - {"margin", "markup"} <= MONEY_FIELDS


def test_localized_preview_preserves_underlying_financial_data_and_order():
    rows = [
        {"sku": "0001", "currency": "IRR", "normal_price": D(12340), "status": "VALID"},
        {"sku": "0002", "currency": "USD", "normal_price": D(10), "status": "INVALID"},
    ]
    original = deepcopy(rows)
    table = preview(rows, language="fa", display_currency="TOMAN", persian_digits=True)
    assert table["قیمت فروش عادی"].tolist() == ["۱٬۲۳۴", "۱۰"]
    assert table["واحد پول"].tolist() == ["تومان", "USD"]
    assert table["وضعیت"].tolist() == ["معتبر", "نیازمند اصلاح"]
    assert table.columns[-1] == "شناسه کالا"
    assert rows == original
    english = preview(rows, language="en")
    assert english["Status"].tolist() == ["VALID", "INVALID"]


def test_filters_follow_row_identity_across_all_sections_not_duplicate_sku():
    result = calculate_catalog(
        [{"sku": "A", "purchase_cost": 100}, {"sku": "B", "purchase_cost": ""}],
        currency="IRR",
        target_margin="10%",
    )
    original = deepcopy(result)
    valid = filter_results(result, "valid")
    invalid = filter_results(result, "invalid")
    assert [r["sku"] for r in valid["Product_Calculations"]] == ["A"]
    assert not valid["Errors"]
    assert [r["sku"] for r in invalid["Product_Calculations"]] == ["B"]
    assert invalid["Errors"] and not invalid["Price_Recommendations"]
    assert result == original


def test_market_switch_excludes_other_market_columns_without_mapping_prompts():
    row = {
        "قیمت خرید": 100,
        "کمیسیون دیجی کالا": "10%",
        "قیمت فروش دیجی": 150,
        "کمیسیون اسنپ": "20%",
        "قیمت فروش اسنپ": 160,
        "تپسی شاپ کمیسیون": "15%",
        "amazon shipping cost": 30,
        "ebay commission": "5%",
    }
    for market, expected in [
        ("digikala", ".1"),
        ("snapp_shop", ".2"),
        ("tapsi_shop", ".15"),
        ("ebay", ".05"),
    ]:
        mapping = scoped_mapping(list(row), market, suggest_mapping(list(row), market))
        assert all(mapping[h] == IGNORE for h in excluded_columns(list(row), market))
        parsed = map_rows([row], mapping)[0]
        assert D(parsed["commission_rate"].strip("%")) / 100 == D(expected)
    assert "commission_rate" in matching_fields("digikala")
    assert "payment_rate" in matching_fields("custom")
    assert "fulfillment" in matching_fields("amazon")
    assert "customs_duty" in matching_fields("custom", advanced=True)
    assert set(CHANNELS) <= load_profiles().keys()


def test_custom_website_uses_own_selling_price_and_ignores_market_columns():
    headers = ["قیمت خرید", "قیمت سایت", "قیمت فروش اسنپ"]
    mapping = scoped_mapping(headers, "custom", suggest_mapping(headers, "custom"))
    assert mapping["قیمت سایت"] == "current_price"
    assert mapping["قیمت فروش اسنپ"] == IGNORE


def test_language_switch_retains_financial_settings_and_renders_both_workspaces():
    app = AppTest.from_file(Path("app.py").resolve()).run()
    app.text_input(key="target_margin").set_value("22%").run()
    app.selectbox(key="sales_channel__en").select("digikala").run()
    app.radio(key="ui_language").set_value("fa").run()
    assert not app.exception
    assert app.text_input(key="target_margin").value == "22%"
    assert app.selectbox(key="sales_channel__fa").value == "digikala"
    assert app.selectbox(key="sales_channel__fa").label == "کالاها را کجا می‌فروشید؟"
    assert app.checkbox(key="digits_fa").value
    app.radio(key="workspace").set_value("Actual profit (سود واقعی)").run()
    next(b for b in app.button if b.label == "امتحان با داده نمونه").click().run()
    assert not app.exception
    assert any(h.value == "مقایسه بازارها" for h in app.subheader)
    app.radio(key="ui_language").set_value("en").run()
    assert not app.exception
    assert any(h.value == "Platform Comparison" for h in app.subheader)


def test_primary_actions_have_complete_translations():
    for text in [
        "Validate and calculate",
        "Download results workbook",
        "Column mapping",
        "Only valid products",
        "Only invalid products",
        "Automatically excluded columns",
    ]:
        assert translate(text, "fa") != text
