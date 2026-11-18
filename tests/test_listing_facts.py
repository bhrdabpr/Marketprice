from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

from marketprice.io import workbook_bytes
from marketprice.listing_facts import check_claims, parse_facts
from marketprice.listings import review_listings


def fact(**changes):
    return {"fact_id": "F1", "sku": "001", "subject": "bottle", "attribute": "insulated",
            "value": "false", "unit": "", "status": "confirmed", "source": "Synthetic supplier sheet",
            "source_locator": "B2", **changes}


def review(title="Bottle is insulated", facts=None, **kwargs):
    return review_listings([{"sku": "001", "title": title}],
                           fact_rows=facts if facts is not None else [fact()], **kwargs)


@pytest.mark.parametrize("change", [
    {"source": ""}, {"sku": 123}, {"sku": ""}, {"subject": ""}, {"fact_id": ""},
    {"value": "yes"}, {"attribute": "invented"}, {"status": "approved"}, {"unit": "ml"},
    {"unexpected": "x"},
    {"attribute": "height", "value": "20", "unit": "ml"},
    {"attribute": "height", "value": "NaN", "unit": "cm"},
    {"attribute": "height", "value": "Infinity", "unit": "cm"},
    {"attribute": "height", "value": "-1", "unit": "cm"},
    {"attribute": "height", "value": "1,000", "unit": "cm"},
    {"attribute": "height", "value": "0.123456789123456789123", "unit": "cm"},
    {"attribute": "pack_count", "value": "1.5"},
])
def test_invalid_facts_are_rejected(change):
    with pytest.raises(ValueError, match="FACT_"):
        parse_facts([fact(**change)])


def test_duplicate_ids_and_orphan_skus_rejected():
    with pytest.raises(ValueError, match="FACT_DUPLICATE_ID"):
        parse_facts([fact(), fact()])
    with pytest.raises(ValueError, match="FACT_SKU_MISMATCH"):
        review(facts=[fact(sku="other")])


def test_negative_fact_blocks_claim_and_links_source():
    result = review(facts_confirmed=True)
    check = result["Claim_Checks"][0]
    assert check["status"] == "CONTRADICTED_CLAIM" and check["fact_ids"] == "F1"
    assert any(i["code"] == "CONTRADICTED_CLAIM" and i["severity"] == "ERROR" for i in result["Listing_Issues"])
    assert result["Product_Facts"][0]["source_locator"] == "B2"
    assert not result["Listing_Summary"][0]["decision_ready"]


@pytest.mark.parametrize("title", ["Bottle is not insulated", "Bottle is non-insulated", "Bottle is never insulated"])
def test_negative_claim_can_match_negative_fact(title):
    assert review(title, facts_confirmed=True)["Claim_Checks"][0]["status"] == "SUPPORTED_FACT"


@pytest.mark.parametrize("title", ["Bottle may be insulated", "Bottle is not only insulated", "Bottle with cap that is insulated", "Not bottle is insulated"])
def test_uncertain_or_component_scope_is_never_supported(title):
    assert all(c["status"] != "SUPPORTED_FACT" for c in review(title, facts=[fact(value="true")],
                                                             facts_confirmed=True)["Claim_Checks"])


def test_unreviewed_and_unverified_facts_cannot_support_claim():
    assert review("Bottle is not insulated")["Claim_Checks"][0]["status"] == "UNSUPPORTED_CLAIM"
    result = review(facts=[fact(value="true", status="unverified")], facts_confirmed=True)
    assert result["Claim_Checks"][0]["status"] == "UNSUPPORTED_CLAIM"
    assert not result["Product_Facts"][0]["eligible"]


@pytest.mark.parametrize("second", [fact(fact_id="F2", value="true"), fact(fact_id="F2", status="disputed")])
def test_conflicting_or_disputed_fact_blocks_support(second):
    result = review("Bottle is not insulated", facts=[fact(), second], facts_confirmed=True)
    assert result["Claim_Checks"][0]["status"] == "FACT_CONFLICT"
    assert all(not f["eligible"] for f in result["Product_Facts"])


def test_duplicate_listing_identity_does_not_select_variant_facts():
    result = review_listings([{"sku": "001", "title": "Bottle is not insulated"}] * 2,
                             fact_rows=[fact()], facts_confirmed=True)
    assert sum(i["code"] == "INVALID_IDENTITY" for i in result["Listing_Issues"]) == 2
    assert all(c["status"] != "SUPPORTED_FACT" for c in result["Claim_Checks"])
    assert not result["Product_Facts"][0]["eligible"]


def test_component_dimensions_and_unit_conversion():
    facts = [fact(attribute="height", value="20", unit="cm"),
             fact(fact_id="F2", subject="cap", attribute="height", value="5", unit="cm")]
    swapped = review("Bottle height 5 cm; cap height 20 cm", facts, facts_confirmed=True)
    assert [c["status"] for c in swapped["Claim_Checks"]] == ["CONTRADICTED_CLAIM"] * 2
    equivalent = review("Bottle height 200 mm; cap height 0.05 m", facts, facts_confirmed=True)
    assert [c["status"] for c in equivalent["Claim_Checks"]] == ["SUPPORTED_FACT"] * 2
    unknown = review("Bottle height 8 inches", facts, facts_confirmed=True)
    assert unknown["Claim_Checks"][0]["status"] == "MEASUREMENT_REVIEW"
    assert check_claims("Not bottle height 20 cm", parse_facts(facts))[0]["status"] == "MEASUREMENT_REVIEW"


def test_repeated_equivalent_sources_are_not_a_conflict():
    result = review("Bottle height 20 cm", [fact(attribute="height", value="20", unit="cm"),
                   fact(fact_id="F2", attribute="height", value="200", unit="mm")], facts_confirmed=True)
    assert result["Claim_Checks"][0]["status"] == "SUPPORTED_FACT"


def test_legacy_negation_and_unsupported_assertions_are_visible():
    result = review_listings([{"sku": "001", "title": "Dishwasher safe bottle 32 oz",
                               "reference": "Bottle is not insulated", "keywords": "insulated bottle"}],
                              reference_confirmed=True)
    assert result["Keyword_Review"][0]["status"] == "NEGATION_REVIEW"
    codes = {i["code"] for i in result["Listing_Issues"]}
    assert {"UNSUPPORTED_CLAIM", "MEASUREMENT_SCOPE_REVIEW", "CONTENT_COMPLETENESS_REVIEW"} <= codes
    assert result["Listing_Summary"][0]["status"] == "REVIEW_REQUIRED"
    assert "Arabic" in result["Check_Coverage"][0]["not_checked"]


def test_source_text_is_literal_in_export():
    result = review(facts=[fact(source='=HYPERLINK("example")')], facts_confirmed=True)
    book = load_workbook(BytesIO(workbook_bytes(result)))
    assert {"Product_Facts", "Claim_Checks", "Check_Coverage"} <= set(book.sheetnames)
    assert all(cell.data_type != "f" for sheet in book for row in sheet for cell in row)
    book.close()


def test_fact_ui_report_invalidates_when_review_changes():
    app = AppTest.from_file(str(Path("app.py").resolve())).run()
    app.button(key="tool_listings").click().run()
    app.checkbox(key="listing_demo_0").check().run()
    app.checkbox(key="listing_facts_demo_0").check().run()
    confirmation = next(c for c in app.checkbox if c.key.startswith("listing_facts_confirm_"))
    confirmation.check().run()
    app.button(key="listing_run").click().run()
    assert not app.exception
    result = app.session_state["listing_result"][1]
    assert len(result["Product_Facts"]) == 3
    assert result["Product_Facts"][0]["eligible"]
    assert not result["Product_Facts"][2]["eligible"]
    assert result["Sources"][1]["role"] == "structured_product_facts"
    next(c for c in app.checkbox if c.key.startswith("listing_facts_confirm_")).uncheck().run()
    assert not any(d.proto.label == "Download listing review workbook" for d in app.get("download_button"))
    app.button(key="clear_session").click().run()
    assert "listing_result" not in app.session_state


def test_numeric_listing_sku_cannot_select_facts():
    result = review_listings([{"sku": 123, "title": "Bottle is not insulated"}],
                             fact_rows=[fact(sku="123")], facts_confirmed=True)
    assert not result["Product_Facts"][0]["eligible"]
    assert result["Claim_Checks"][0]["status"] != "SUPPORTED_FACT"


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_uploaded_facts_and_invalid_replacement_hide_report(monkeypatch, extension):
    import csv
    from io import StringIO

    import streamlit as st

    from marketprice.io import read_upload
    from marketprice.listings_ui import FACT_SAMPLE

    rows = read_upload(FACT_SAMPLE, "facts.csv", preserve_headers=True)
    payload = FACT_SAMPLE if extension == "csv" else workbook_bytes({"Facts": rows})

    class Upload:
        name = "facts." + extension

        def getvalue(self):
            return payload

    monkeypatch.setattr(st, "file_uploader", lambda *args, key="", **kwargs:
                        Upload() if key.startswith("listing_facts_upload_") else None)
    app = AppTest.from_file(str(Path("app.py").resolve())).run()
    app.button(key="tool_listings").click().run()
    app.checkbox(key="listing_demo_0").check().run()
    next(c for c in app.checkbox if c.key.startswith("listing_facts_confirm_")).check().run()
    app.button(key="listing_run").click().run()
    assert not app.exception
    result = app.session_state["listing_result"][1]
    assert len(result["Product_Facts"]) == 3
    assert result["Product_Facts"][0]["eligible"]
    rows[0]["source"] = ""
    if extension == "xlsx":
        payload = workbook_bytes({"Facts": rows})
    else:
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        payload = buffer.getvalue().encode()
    app.run()
    assert not app.exception
    assert any("FACT_SOURCE" in e.value for e in app.error)
    assert not any(d.proto.label == "Download listing review workbook" for d in app.get("download_button"))
