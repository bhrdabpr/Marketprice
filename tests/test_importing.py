from decimal import Decimal

import pytest

from marketprice.flexible import calculate_catalog
from marketprice.importing import IGNORE, UNMAPPED, available_markets, map_rows, suggest_mapping
from marketprice.io import read_upload


def test_original_headers_and_ambiguous_mapping():
    rows = read_upload("قیمت خرید,هزیته ارسال,mystery\n100,5,abc\n".encode(), "a.csv", preserve_headers=True)
    mapping = suggest_mapping(list(rows[0]))
    assert mapping == {"قیمت خرید": "purchase_cost", "هزیته ارسال": "shipping", "mystery": UNMAPPED}
    with pytest.raises(ValueError, match="Resolve"):
        map_rows(rows, mapping)
    mapping["mystery"] = IGNORE
    assert map_rows(rows, mapping) == [{"purchase_cost": "100", "shipping": "5"}]


def test_marketplace_columns_never_mix():
    row = {
        "کد": "A",
        "کد کالا": "0001",
        "قیمت خرید": 100,
        " کمیسیون اسنپ": ".095",
        "کمیسیون دیجی کالا ": ".1",
        "قیمت فروش دیجی": 150,
        "قیمت فروش اسنپ": 160,
        "هزینه ارسال دیجی کالا": 10,
        "هزینه ارسال اسنپ شاپ": 20,
        "قیمت درست اسنپ تومان": 999,
        "حداقل مارجین ۵  دیجی": 999,
    }
    assert available_markets(list(row)) == ["digikala", "snapp_shop"]
    digi = map_rows([row], suggest_mapping(list(row), "digikala"))[0]
    snapp = map_rows([row], suggest_mapping(list(row), "snapp_shop"))[0]
    assert digi == {
        "sku": "A",
        "purchase_cost": 100,
        "commission_rate": ".1",
        "current_price": 150,
        "shipping": 10,
    }
    assert snapp["current_price"] == 160 and snapp["shipping"] == 20
    assert snapp["commission_rate"] == ".095"


def test_explicit_units_and_row_error_isolation():
    rows = [{"buy": 10, "comision": 10}, {"buy": False, "comision": ""}]
    mapped = map_rows(
        rows,
        {"buy": "purchase_cost", "comision": "commission_rate"},
        {"buy": "TOMAN → IRR", "comision": "Percentage number"},
    )
    assert mapped[0]["purchase_cost"] == 100
    assert mapped[0]["commission_rate"] == Decimal(".1")
    result = calculate_catalog(mapped, currency="IRR", target_margin="10%")
    assert [r["status"] for r in result["Product_Calculations"]] == ["VALID", "INVALID"]
    assert result["Price_Recommendations"][0]["recommended_price"] == 125


def test_duplicate_mapping_needs_review():
    with pytest.raises(ValueError, match="DUPLICATE_COLUMNS"):
        map_rows([{"a": 10, "b": 20}], {"a": "purchase_cost", "b": "purchase_cost"})
