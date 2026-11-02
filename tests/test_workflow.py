import io
from decimal import Decimal as D

import pytest
from openpyxl import load_workbook

from marketprice.batch import process
from marketprice.io import read_upload, workbook_bytes
from marketprice.samples import sample_row, sample_rows
from marketprice.validation import number


def test_workbook_roundtrip_and_reconciliation():
    incoming = workbook_bytes({"Products": sample_rows()})
    result = process(read_upload(incoming, "input.xlsx"))
    book = load_workbook(io.BytesIO(workbook_bytes(result)), data_only=False)
    assert book.sheetnames == list(result)
    assert book["Product_Calculations"].max_row == 4
    assert result["Summary"][1]["value"] == 2
    assert result["Price_Recommendations"][0]["recommended_price"] == D("117.65")
    assert result["Errors"][0]["sku"] == "ERROR-003"
    assert all(c.data_type != "f" for s in book for row in s for c in row)


def test_formula_injection():
    for text in ['=HYPERLINK("https://evil.invalid")', "+cmd", "-cmd", "@SUM(A1)", "\t=1+1"]:
        output = workbook_bytes({"Products": [{**sample_row(), "name": text}]})
        book = load_workbook(io.BytesIO(output))
        assert book["Products"]["B2"].data_type == "s"
        assert book["Products"]["B2"].value == text


@pytest.mark.parametrize(
    "blob,name",
    [
        (b"not zip", "x.xlsx"),
        (b"\xff", "x.csv"),
        (b"a,a\n1,2", "x.csv"),
        (b"a\n1,2", "x.csv"),
        (b"a", "x.exe"),
    ],
)
def test_corrupt(blob, name):
    with pytest.raises(ValueError):
        read_upload(blob, name)


def test_numerals_and_aliases():
    assert number("۱۲٬۳۴۵٫۶۷", "fa") == D("12345.67")
    assert number("١٠٪", "fa") == D(".1")
    assert number("1.234,56", "comma") == D("1234.56")
    with pytest.raises(ValueError):
        number("12,34")
    data = read_upload("کد کالا,هزینه ارسال\n۰۰۱,۰\n".encode(), "test.csv")
    assert data[0]["sku"] == "۰۰۱"


def test_unknown_cost_not_ignored():
    result = process([{**sample_row(), "surprise_cost": "100"}])
    assert result["Errors"] and not result["Price_Recommendations"]


def test_thousand_independent_rows():
    rows = [{**sample_row(f"SKU-{i}"), "purchase_cost": str(i + 1)} for i in range(1000)]
    result = process(rows)
    assert not result["Errors"] and len(result["Price_Recommendations"]) == 1000
    for i, record in enumerate(result["Price_Recommendations"]):
        expected = ((D(i + 11) / D(".68")) * 100).to_integral_value(rounding="ROUND_CEILING") / 100
        assert record["recommended_price"] == expected


def test_multiple_targets_constraints():
    result = process([sample_row()], margins=(D(".1"), D(".3")))
    assert len(result["Price_Recommendations"]) == 3
    assert not process([{**sample_row(), "price_ceiling": "100"}])["Price_Recommendations"]


def test_app_initial():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file("../app.py").run(timeout=30)
    assert not app.exception
    assert app.title[0].value == "MarketPrice"
