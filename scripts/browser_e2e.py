"""Real browser upload, calculation, download, and workbook reconciliation."""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

url = "http://127.0.0.1:8501"
for _ in range(100):
    try:
        urllib.request.urlopen(url + "/_stcore/health", timeout=1).close()
        break
    except (urllib.error.URLError, TimeoutError):
        time.sleep(0.2)
else:
    raise RuntimeError("Start the app before running browser E2E")
Path("docs").mkdir(exist_ok=True)
Path("reports").mkdir(exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1080}, device_scale_factor=1)
    page.goto(url)
    page.get_by_role("heading", name="MarketPrice", exact=True).wait_for(timeout=30000)
    page.screenshot(path="docs/screenshot-upload.png", full_page=True)
    page.locator("input[type=file]").set_input_files("samples/sample_input.xlsx")
    page.get_by_role("combobox", name="Worksheet to analyze", exact=True).wait_for(timeout=30000)
    page.get_by_text("I reviewed the column meanings, ignored columns and units", exact=True).click()
    assert page.get_by_role(
        "checkbox", name="I reviewed the column meanings, ignored columns and units"
    ).is_checked()
    page.get_by_role("button", name="Validate and calculate", exact=True).click(timeout=30000)
    page.get_by_role("button", name="Prepare complete Excel report", exact=True).click()
    download_button = page.get_by_role("button", name="Download results workbook", exact=True)
    download_button.wait_for(timeout=30000)
    with page.expect_download() as item:
        download_button.click()
    item.value.save_as("reports/browser_download.xlsx")
    page.mouse.move(1100, 800)
    page.mouse.wheel(0, 650)
    page.wait_for_timeout(500)
    page.screenshot(path="docs/screenshot-results.png", full_page=True)
    page.get_by_role("tab", name="Campaigns", exact=True).click()
    page.get_by_text("Sales multiplier: 1.25 means", exact=False).wait_for()
    page.get_by_text("Competitor-backed promotion review", exact=True).click()
    page.get_by_role("button", name="Download competitor evidence template", exact=True).wait_for()
    page.get_by_role("tab", name="Errors & warnings").click()
    page.screenshot(path="docs/screenshot-errors.png", full_page=True)
    book = load_workbook("reports/browser_download.xlsx", data_only=True)
    assert len(book.sheetnames) == 14
    sheet = book["Price_Recommendations"]
    records = list(sheet.values)
    headers = records[0]
    rows = [dict(zip(headers, row)) for row in records[1:]]
    golden = next(row for row in rows if row["sku"] == "GOLDEN-001" and float(row["target_margin"]) == 0.2)
    assert golden["recommended_price"] == 117.65
    assert book["Product_Calculations"].max_row == 4
    assert book["Price_Analysis"].max_row == 7
    assert book["Seasonal_Campaigns"].max_row == 5
    assert {row["target_margin"] for row in rows if row["sku"] == "GOLDEN-001"} == {0.15, 0.2, 0.25}
    assert any("MISSING_SHIPPING_COST" in str(row) for row in book["Errors"].values)
    assert page.get_by_text("Processing failed safely.", exact=False).count() == 0
    report = {
        "status": "PASS",
        "browser": browser.version,
        "upload": "samples/sample_input.xlsx",
        "download": "reports/browser_download.xlsx",
        "sheets": book.sheetnames,
        "golden_price": 117.65,
        "invalid_product_retained": True,
    }
    Path("reports/browser-e2e.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    page.get_by_text("Only invalid products", exact=True).click()
    assert page.get_by_role("radio", name="Only invalid products", exact=True).is_checked()
    page.get_by_text("فارسی", exact=True).click()
    page.get_by_text("فقط کالاهای معتبر", exact=True).click()
    assert page.get_by_role("radio", name="فقط کالاهای معتبر", exact=True).is_checked()
    assert page.locator('[data-testid="stMain"]').evaluate("el => getComputedStyle(el).direction") == "rtl"
    page.get_by_text("English", exact=True).click()
    page.get_by_text("Specialist tools", exact=True).click()
    page.get_by_text("Actual profit", exact=True).click()
    page.get_by_role("button", name="Try synthetic demo", exact=True).click()
    actual_download = page.get_by_role("button", name="Download reconciliation evidence", exact=True)
    actual_download.wait_for(timeout=30000)
    with page.expect_download() as actual_item:
        actual_download.click()
    actual_item.value.save_as("reports/browser_actuals.xlsx")
    actual_book = load_workbook("reports/browser_actuals.xlsx", data_only=True)
    actual_rows = list(actual_book["Platform_Comparison"].values)
    actual_records = [dict(zip(actual_rows[0], r)) for r in actual_rows[1:]]
    assert [r["contribution"] for r in actual_records] == [800, 850]
    assert actual_book["Product_Platform"].max_row == 3
    actual_book.close()
    print("Actual-profit browser demo and download reconciled: 800 / 850 IRR")
    browser.close()
