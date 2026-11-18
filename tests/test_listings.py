from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

from marketprice.io import read_upload, workbook_bytes
from marketprice.listings import map_listing_rows, quantities, review_listings, suggest_listing_mapping
from marketprice.listings_ui import SAMPLE


def test_example_conflicts_keywords_and_export():
    raw = read_upload(SAMPLE, "example.csv", preserve_headers=True)
    rows = map_listing_rows(raw, suggest_listing_mapping(list(raw[0])))
    result = review_listings(rows, reference_confirmed=True)
    assert any(i["code"] == "QUANTITY_CONFLICT" for i in result["Listing_Issues"])
    assert {k["keyword"]: k["status"] for k in result["Keyword_Review"]} == {
        "steel bottle": "WORDS_PRESENT_REVIEW_REQUIRED",
        "gaming laptop": "REVIEW_RELEVANCE",
        "best": "VAGUE",
    }
    assert result["Original_Listings"][0]["title"] == raw[0]["title"]
    book = load_workbook(BytesIO(workbook_bytes(result)))
    assert book["Listing_Issues"].max_row > 1


def test_unknown_facts_not_false_success_and_no_synonym_verdict():
    row = {"sku": "001", "title": "Flask", "reference": "bottle capacity 500 ml", "keywords": "flask"}
    result = review_listings([row])
    assert result["Keyword_Review"][0]["status"] == "NEEDS_EVIDENCE"
    result = review_listings([row], reference_confirmed=True)
    assert result["Keyword_Review"][0]["status"] == "REVIEW_RELEVANCE"
    assert not result["Listing_Summary"][0]["decision_ready"]


@pytest.mark.parametrize("brand", ["Generic", " generic ", "UNBRANDED", "No brand"])
def test_generic_brand_does_not_require_title_keyword(brand):
    row = {
        "sku": "GEN-1",
        "title": "Steel bottle 500 ml",
        "brand": brand,
        "model": "M500",
        "reference": "Steel bottle 500 ml model M500",
    }
    result = review_listings([row], reference_confirmed=True)
    identity = [i for i in result["Listing_Issues"] if i["code"] == "IDENTITY_NOT_IN_TITLE"]
    assert [i["observed"] for i in identity] == ["M500"]
    assert result["Original_Listings"][0]["brand"] == brand


def test_real_brand_remains_an_identity_review():
    row = {
        "sku": "BR-1",
        "title": "Steel bottle",
        "brand": "ExampleBrand",
        "reference": "ExampleBrand steel bottle",
    }
    result = review_listings([row], reference_confirmed=True)
    assert any(
        i["code"] == "IDENTITY_NOT_IN_TITLE" and i["observed"] == "ExampleBrand"
        for i in result["Listing_Issues"]
    )


def test_units_persian_and_identity():
    assert quantities("۰٫۵ لیتر") == quantities("500 ml")
    assert quantities("1,500 ml") == {}  # Ambiguous grouping must not become 500 ml.
    assert quantities("۵۰۰ میلی‌لیتر") == quantities("0.5 L")
    rows = [{"sku": "001", "title": "Bottle 0.5 L", "reference": "Bottle 500 ml"}]
    result = review_listings(rows, reference_confirmed=True)
    assert not any(i["code"] == "QUANTITY_CONFLICT" for i in result["Listing_Issues"])
    assert any(i["code"] == "INVALID_IDENTITY" for i in review_listings(rows * 2)["Listing_Issues"])


def test_file_delimiters_and_formula_export():
    rows = read_upload(
        b'sku;title;description\n00123;Bottle;"Line one\nLine two"\n',
        "x.csv",
        preserve_headers=True,
        delimiter=";",
    )
    assert rows[0]["sku"] == "00123"
    assert rows[0]["description"] == "Line one\nLine two"
    result = review_listings([{"sku": "=1+1", "title": '=HYPERLINK("bad")'}])
    book = load_workbook(BytesIO(workbook_bytes(result)))
    assert all(c.data_type != "f" for ws in book for row in ws for c in row)
    with pytest.raises(ValueError, match="Duplicate mapping"):
        map_listing_rows([], {"a": "sku", "b": "sku"})


@pytest.mark.parametrize("language", ["en", "fa"])
def test_workspace_demo_and_stale_report(language):
    app = AppTest.from_file(str(Path("app.py").resolve())).run()
    app.radio(key="ui_language").set_value(language).run()
    app.radio(key="workspace__" + language).set_value("Listings").run()
    app.checkbox(key="listing_demo_0").check().run()
    next(c for c in app.checkbox if c.key.startswith("listing_reference_")).check().run()
    app.button(key="listing_run").click().run()
    assert not app.exception
    assert any(
        d.proto.label in {"Download listing review workbook", "دریافت گزارش اکسل محتوا"}
        for d in app.get("download_button")
    )
    next(c for c in app.checkbox if c.key.startswith("listing_reference_")).uncheck().run()
    assert not any(
        d.proto.label in {"Download listing review workbook", "دریافت گزارش اکسل محتوا"}
        for d in app.get("download_button")
    )


def test_xlsx_upload_ui(monkeypatch):
    import streamlit as st

    raw = read_upload(SAMPLE, "sample.csv", preserve_headers=True)
    payload = workbook_bytes({"Catalog": raw})

    class Upload:
        name = "catalog.xlsx"

        def getvalue(self):
            return payload

    monkeypatch.setattr(
        st,
        "file_uploader",
        lambda *args, key="", **kwargs: Upload() if key.startswith("listing_upload_") else None,
    )
    app = AppTest.from_file(str(Path("app.py").resolve())).run()
    app.radio(key="workspace__en").set_value("Listings").run()
    next(c for c in app.checkbox if c.key.startswith("listing_reference_")).check().run()
    app.button(key="listing_run").click().run()
    assert not app.exception
    result = app.session_state["listing_result"][1]
    assert result["Sources"][0]["sheet"] == "Catalog"
    assert any(i["code"] == "QUANTITY_CONFLICT" for i in result["Listing_Issues"])
    app.button(key="clear_session").click().run()
    assert "listing_result" not in app.session_state
