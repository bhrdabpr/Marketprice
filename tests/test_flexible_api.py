import io
import json
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from marketprice.api import create_app
from marketprice.batch import COST_FIELDS
from marketprice.flexible import calculate_catalog
from marketprice.integrations import calculate_marketplace
from marketprice.io import read_upload, workbook_bytes

SETTINGS = {"currency": "IRR", "target_margin": "10%"}
TOKEN = "test-token-not-a-real-secret-12345"


def catalog(rows, **settings):
    return calculate_catalog(rows, **{**SETTINGS, **settings})


def test_purchase_and_fixed_tax_only():
    rows = read_upload(workbook_bytes({"Products": [{"purchase_cost": 100, "other_fixed": 10}]}), "a.xlsx")
    result = catalog(rows)
    assert result["Product_Calculations"][0]["status"] == "VALID"
    assert result["Price_Recommendations"][0]["recommended_price"] == 123
    assert not result["Campaign_Simulations"]
    assert "profit" not in result["Product_Calculations"][0]
    assert "input_current_price" not in result["Audit_Trail"][0]


def test_sales_tax_expense_and_margin_independent_formula():
    result = catalog([{"purchase_cost": 100, "transaction_tax_rate": "10%", "current_price": 150}])
    row = result["Product_Calculations"][0]
    assert row["recommended_price"] == 125  # 100 / (1 - .1 tax - .1 margin)
    assert row["profit"] == 35
    assert row["margin"] == Decimal(35) / Decimal(150) or abs(row["margin"] - Decimal(35) / 150) < Decimal(
        "1e-27"
    )
    assert any(c["safe"] for c in result["Campaign_Simulations"])
    assert all(c["margin"] >= Decimal(".1") for c in result["Campaign_Simulations"] if c["safe"])


@pytest.mark.parametrize("bad", [None, "", False, "nonsense", "-2", "101%"])
def test_included_commission_bad_cell_only_invalidates_its_product(bad):
    result = catalog(
        [
            {"purchase_cost": 100, "commission_rate": "5%"},
            {"purchase_cost": 100, "commission_rate": bad},
            {"purchase_cost": 100, "commission_rate": 0},
        ]
    )
    assert [r["status"] for r in result["Product_Calculations"]] == ["VALID", "INVALID", "VALID"]


def test_ragged_json_cost_missing_in_one_row_is_not_zero():
    result = catalog([{"purchase_cost": 100}, {"purchase_cost": 100, "shipping": 5}])
    assert [r["status"] for r in result["Product_Calculations"]] == ["INVALID", "VALID"]


def test_mixed_currencies_use_correct_grid():
    result = catalog([{"purchase_cost": 100, "currency": "USD"}, {"purchase_cost": 100, "currency": "IRR"}])
    assert [r["recommended_price"] for r in result["Price_Recommendations"]] == [Decimal("111.12"), 112]


def test_unknown_column_requires_mapping_and_missing_cost_is_invalid():
    with pytest.raises(ValueError, match="Map or explicitly ignore"):
        catalog([{"buy": 100}])
    result = catalog([{"purchase_cost": None}])
    assert result["Summary"][2]["value"] == 1


def test_ten_thousand_eleven_costs():
    costs = dict.fromkeys(sorted(COST_FIELDS)[:11], "0")
    rows = [{"sku": str(i), "purchase_cost": "100", **costs} for i in range(10000)]
    rows[5000]["commission_rate"] = None
    result = catalog(rows, discounts=())
    assert [s["value"] for s in result["Summary"][:3]] == [10000, 9999, 1]
    assert result["Price_Recommendations"][0]["recommended_price"] == 112
    assert all(r["sku"] != "5000" for r in result["Price_Recommendations"])


def api_call(payload, token=TOKEN, method="POST", path="/v1/calculate"):
    raw = json.dumps(payload).encode()
    statuses = []
    result = create_app(TOKEN)(
        {
            "PATH_INFO": path,
            "REQUEST_METHOD": method,
            "HTTP_AUTHORIZATION": "Bearer " + token,
            "CONTENT_LENGTH": str(len(raw)),
            "wsgi.input": io.BytesIO(raw),
        },
        lambda status, headers: statuses.append(status),
    )
    return statuses[0], json.loads(b"".join(result))


def test_api_matches_excel_calculation():
    payload = {"products": [{"purchase_cost": "100", "transaction_tax_rate": "10%"}], "settings": SETTINGS}
    status, data = api_call(payload)
    assert status == "200 OK"
    assert data["Price_Recommendations"][0]["recommended_price"] == "125"
    assert data["Product_Calculations"][0]["current_price_status"] == "NOT_PROVIDED"


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"products": "bad"},
        {"products": [{}], "settings": {"currency": "USD", "target_margin": "NaN"}},
        {"products": [[]], "settings": SETTINGS},
        {"products": [{"purchase_cost": 10}], "settings": {**SETTINGS, "secret": "bad"}},
    ],
)
def test_api_bad_requests(payload):
    assert api_call(payload)[0] == "400 Bad Request"


def test_api_auth_and_routes():
    assert api_call({}, token="wrong")[0] == "401 Unauthorized"
    assert api_call({}, method="GET")[0] == "405 Method Not Allowed"
    assert api_call({}, path="/wrong")[0] == "404 Not Found"
    with pytest.raises(ValueError):
        create_app("short")


def test_future_marketplace_adapter_joins_costs_without_guessing():
    class FixtureAdapter:
        def fetch_listings(self):
            return [
                {"sku": "A", "current_price": "150", "currency": "IRR"},
                {"sku": "B", "current_price": "160", "currency": "IRR"},
            ]

    result = calculate_marketplace(FixtureAdapter(), {"A": {"purchase_cost": "100"}}, **SETTINGS)
    assert [r["status"] for r in result["Product_Calculations"]] == ["VALID", "INVALID"]
    assert result["Campaign_Simulations"]
    with pytest.raises(ValueError, match="must not overwrite"):
        calculate_marketplace(FixtureAdapter(), {"A": {"currency": "USD"}}, **SETTINGS)


def test_ui_starts_with_flexible_controls():
    app = AppTest.from_file(Path("app.py").resolve()).run()
    assert not app.exception
    assert next(c for c in app.checkbox if c.label.startswith("Flexible catalog")).value
    assert any(t.label.startswith("Target margin") for t in app.text_input)
