from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from marketprice import listing_urls
from marketprice.listing_urls import parse_page, product_url, read_products

ASIN = "B000000001"
URL = "https://www.amazon.ae/dp/" + ASIN
PAGE = f"""
<html><head><link rel="canonical" href="{URL}"></head>
<body><div id="title"><span id="productTitle">Kitchen &amp; home opener</span></div>
<div id="feature-bullets"><ul><li><span>Steel <b>grip</b></span></li></ul></div>
<div id="productDescription">First line<br>Second line<script>ignore me</script></div>
<div>Related products</div></body></html>""".encode()


def test_reads_selected_fields_and_verifies_saved_page_identity():
    assert parse_page(PAGE, "amazon.ae", ASIN, saved=True) == {
        "sku": ASIN, "title": "Kitchen & home opener", "bullet_1": "Steel grip",
        "description": "First line Second line",
    }
    for bad in (PAGE.replace(ASIN.encode(), b"B000000002"), PAGE.replace(b"canonical", b"other"),
                PAGE.replace(b"amazon.ae", b"amazon.com"), b"<title>Site unavailable</title>"):
        with pytest.raises(ValueError):
            parse_page(bad, "amazon.ae", ASIN, saved=True)


@pytest.mark.parametrize("raw", ["http://www.amazon.ae/dp/"+ASIN, "https://other.example/dp/"+ASIN,
                                  "https://amazon.ae.other.example/dp/"+ASIN, "https://amazon.ae/help",
                                  "https://user@amazon.ae/dp/"+ASIN, "https://amazon.com/dp/"+ASIN])
def test_restricts_product_inputs_to_selected_store(raw):
    with pytest.raises(ValueError):
        product_url(raw, "amazon.ae")


def test_batch_deduplicates_canonical_products_and_keeps_partial_results(monkeypatch):
    calls = []

    def fetch(market, asin):
        calls.append(asin)
        if asin != ASIN:
            raise ValueError("HTTP 503")
        return PAGE

    monkeypatch.setattr(listing_urls, "fetch_page", fetch)
    rows, sources = read_products([URL+"?tag=test", URL, URL[:-1]+"2", "invalid"], "amazon.ae")
    assert len(rows) == 1 and calls == [ASIN, ASIN[:-1]+"2"]
    assert [s["status"] for s in sources][:3] == ["Read", "Duplicate link", "HTTP 503"]
    assert sources[0]["source_url"] == URL
    with pytest.raises(ValueError):
        read_products([URL]*21, "amazon.ae")


def test_ui_url_review_preserves_source_and_hides_stale_report(monkeypatch):
    calls = []
    def fetch(market, asin):
        calls.append(asin)
        return PAGE
    monkeypatch.setattr(listing_urls, "fetch_page", fetch)
    app = AppTest.from_file(str(Path("app.py").resolve())).run()
    app.button(key="tool_listings").click().run()
    app.selectbox(key="listing_marketplace").set_value("amazon.ae").run()
    app.radio(key="listing_input_mode").set_value("links").run()
    app.text_area(key="listing_links_links_0").set_value(URL).run()
    app.button(key="listing_read").click().run()
    app.button(key="listing_run").click().run()
    assert not app.exception and calls == [ASIN]
    report = app.session_state["listing_result"][1]
    assert report["Original_Listings"][0]["bullet_1"] == "Steel grip"
    assert report["Sources"][1]["source_url"] == URL
    app.text_area(key="listing_links_links_0").set_value(URL[:-1]+"2").run()
    assert not any(d.proto.label == "Download listing review workbook" for d in app.get("download_button"))
