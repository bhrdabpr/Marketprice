from decimal import Decimal as D
from io import BytesIO

import pytest
from openpyxl import load_workbook

from marketprice.flexible import calculate_catalog
from marketprice.importing import suggest_mapping
from marketprice.io import workbook_bytes
from marketprice.labels import label
from marketprice.models import FIXED_FIELDS, Product


def calc(rows, **options):
    return calculate_catalog(rows, currency="IRR", target_margin="10%", **options)


def test_three_margins_and_break_even_reconciled_independently():
    result = calc(
        [{"purchase_cost": 100, "transaction_tax_rate": "10%", "current_price": 200}],
        margins=(D(".2"), D(".3")),
    )
    assert result["Product_Calculations"][0]["break_even"] == 112
    assert [r["recommended_price"] for r in result["Price_Recommendations"]] == [125, 143, 167]
    assert all(r["actual_margin"] >= r["target_margin"] for r in result["Price_Recommendations"])
    for r in result["Price_Recommendations"]:
        price = r["recommended_price"]
        assert price * (1 - D(".1") - r["target_margin"]) >= 100
        assert (price - 1) * (1 - D(".1") - r["target_margin"]) < 100
    assert all(r["action"] == "DECREASE" for r in result["Price_Analysis"])
    assert all(r["break_even"] == 112 for r in result["Price_Analysis"])


def test_increase_decrease_keep_without_inventory():
    result = calc(
        [{"purchase_cost": 100, "transaction_tax_rate": "10%", "current_price": p} for p in [100, 200, 125]]
    )
    assert [r["action"] for r in result["Price_Analysis"]] == ["INCREASE", "DECREASE", "KEEP"]
    assert all("quantity" not in r for r in result["Price_Analysis"])


def test_seasonal_offers_differ_and_respect_margin_cap_and_costs():
    events = (
        ("Black Friday (جمعه سیاه)", D(".05"), D(0)),
        ("Nowruz (نوروز)", D(".1"), D(20)),
        ("Christmas (کریسمس)", D(".1"), D(1000)),
    )
    result = calc(
        [{"purchase_cost": 100, "transaction_tax_rate": "10%", "current_price": 200}], events=events
    )
    offers = result["Seasonal_Campaigns"]
    assert offers[0]["campaign_price"] == 118
    assert offers[0]["suggested_discount"] == D(".41")
    assert offers[1]["campaign_price"] == 150
    assert offers[1]["suggested_discount"] == D(".25")
    assert offers[2]["status"] == "NO_SAFE_OFFER"
    for r in offers[:2]:
        price = r["campaign_price"]
        cost = 100 + r["campaign_cost"]
        assert price * (1 - D(".1") - r["campaign_margin"]) >= cost
        assert (price - 1) * (1 - D(".1") - r["campaign_margin"]) < cost
        assert r["actual_margin"] >= r["campaign_margin"]
    cap = calc([{"purchase_cost": 100, "current_price": 200, "max_discount": "10%"}], events=events)[
        "Seasonal_Campaigns"
    ][0]
    assert cap["suggested_discount"] == D(".1") and cap["campaign_price"] == 180


def test_missing_current_price_has_no_fabricated_campaign_or_movement():
    result = calc([{"purchase_cost": 100}], events=(("Yalda (یلدا)", D(".05"), D(0)),))
    assert result["Seasonal_Campaigns"] == []
    assert result["Price_Analysis"][0]["action"] == "SET_PRICE"
    assert result["Price_Analysis"][0]["current_price"] is None
    assert result["Price_Analysis"][0]["price_change"] is None


def test_expanded_costs_included_and_blank_row_not_silently_zeroed():
    extra = [f for f in FIXED_FIELDS if not Product.model_fields[f].is_required()]
    good = {"purchase_cost": 100, **dict.fromkeys(extra, 1)}
    result = calc([good, {**good, "financing": None}])
    assert [r["status"] for r in result["Product_Calculations"]] == ["VALID", "INVALID"]
    assert result["Price_Recommendations"][0]["recommended_price"] == 126  # ceil((100+13)/.9)


def test_bilingual_fields_and_workbook_scenario_sections():
    assert all("(" in label(f) for f in Product.model_fields)
    assert suggest_mapping(["حمل ورودی", "Inbound freight"]) == {
        "حمل ورودی": "inbound_freight",
        "Inbound freight": "inbound_freight",
    }
    result = calc(
        [{"purchase_cost": 100, "current_price": 200}],
        margins=(D(".2"), D(".3")),
        events=(("Yalda (یلدا)", D(".05"), D(0)),),
    )
    book = load_workbook(BytesIO(workbook_bytes(result)), data_only=True)
    assert len(book.sheetnames) == 12
    assert book["Price_Recommendations"].max_row == 4
    assert book["Seasonal_Campaigns"].max_row == 2
    assert book["Price_Analysis"].max_row == 4
    book.close()


def test_bad_campaign_configuration_rejected():
    with pytest.raises(ValueError, match="INVALID_CAMPAIGN_SETTINGS"):
        calc([{"purchase_cost": 100}], events=(("test", D(1), D(0)),))
