"""Check isolation between two local browser sessions using synthetic catalogs.

This focused regression test is not a security certification. Start the app
on localhost:8501 first. Nothing is uploaded to an external service.
"""

import os
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

port = int(os.environ.get("MARKETPRICE_TEST_PORT", "8501"))
URL = f"http://127.0.0.1:{port}"
for _ in range(100):
    try:
        with urllib.request.urlopen(URL + "/_stcore/health", timeout=1):
            break
    except (urllib.error.URLError, TimeoutError):
        time.sleep(0.2)
else:
    raise RuntimeError("Start the local app before running the isolation check")

sample = Path("samples/sample_input.csv").read_bytes()
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    first = browser.new_context()
    second = browser.new_context()
    alice = first.new_page()
    bob = second.new_page()
    for page, own in ((alice, b"ALICE-001"), (bob, b"BOB-001")):
        page.goto(URL)
        page.get_by_role("heading", name="Pricing & campaigns", exact=True).wait_for(timeout=30000)
        page.locator("input[type=file]").set_input_files({
            "name": "synthetic.csv", "mimeType": "text/csv",
            "buffer": sample.replace(b"GOLDEN-001", own),
        })
        page.get_by_text("I reviewed the column meanings, ignored columns and units", exact=True).click()
        page.get_by_role("button", name="Validate and calculate", exact=True).click(timeout=30000)
        page.get_by_role("button", name="Prepare complete Excel report", exact=True).click(timeout=30000)

    def exported_skus(page):
        with page.expect_download() as item:
            page.get_by_role("button", name="Download results workbook", exact=True).click()
        book = load_workbook(BytesIO(Path(item.value.path()).read_bytes()), read_only=True, data_only=True)
        values = list(book["Product_Calculations"].values)
        column = values[0].index("sku")
        skus = {str(row[column]) for row in values[1:]}
        book.close()
        return skus

    alice_skus = exported_skus(alice)
    bob_skus = exported_skus(bob)
    assert "ALICE-001" in alice_skus and "BOB-001" not in alice_skus
    assert "BOB-001" in bob_skus and "ALICE-001" not in bob_skus
    alice.get_by_text("Session", exact=True).click()
    alice.get_by_role("button", name="Clear session data").click()
    assert "BOB-001" in exported_skus(bob)
    first.close()
    second.close()
    browser.close()
print("Separate browser sessions exported only their own synthetic catalogs.")
