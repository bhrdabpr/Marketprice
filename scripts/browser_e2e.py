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
    page.get_by_role("heading", name="Pricing & campaigns", exact=True).wait_for(timeout=30000)
    for locale, label in [("فارسی", "قیمت و کمپین"), ("English", "Pricing & campaigns")]:
        page.get_by_text(locale, exact=True).click()
        page.get_by_role("heading", name=label, exact=True).wait_for()
        sidebar = page.locator('[data-testid="stSidebar"]')
        sidebar.hover()
        page.locator('[data-testid="stSidebarCollapseButton"] button').click()
        page.locator(".mp-logo").wait_for(state="hidden")
        page.locator('[data-testid="stExpandSidebarButton"]').click()
        page.locator(".mp-logo").wait_for(state="visible")
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
    page.get_by_role("tab", name="Campaigns", exact=True).click()
    page.get_by_text("Sales multiplier: 1.25 means", exact=False).wait_for()
    page.get_by_text("What if settlement is delayed?", exact=True).click()
    page.get_by_role("spinbutton", name="Additional payment delay (days)", exact=True).fill("30")
    page.get_by_role("spinbutton", name="Annual capital cost (%)", exact=True).fill("36.5")
    page.get_by_text("These are additional costs, not financing already included", exact=True).click()
    with page.expect_download() as delay_item:
        page.get_by_role("button", name="Download settlement scenario evidence", exact=True).click()
    delay_item.value.save_as("reports/settlement-scenario.json")
    delay_data = json.loads(Path("reports/settlement-scenario.json").read_text())
    delay_golden = next(r for r in delay_data["review"] if r["sku"] == "GOLDEN-001" and r["scenario"] == "CURRENT")
    assert float(delay_golden["additional_capital_cost"]) == 2.1
    assert float(delay_golden["contribution_after_delay"]) == 41.1
    assert delay_golden["decision_ready"] is False
    page.get_by_text("Competitor-backed promotion review", exact=True).click()
    page.get_by_role("button", name="Download competitor evidence template", exact=True).wait_for()
    page.get_by_role("tab", name="Errors & warnings").click()
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
    page.get_by_text("Financial performance", exact=True).click()
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
    from marketprice.batch import process
    from marketprice.confidence import apply_confidence
    from marketprice.io import workbook_bytes
    from marketprice.samples import sample_row

    local_reports = Path("reports")
    for label, cost in (("earlier", "70"), ("latest", "80")):
        inputs = [{**sample_row(), "purchase_cost": cost}]
        review = process(inputs)
        apply_confidence(review, inputs, omitted_confirmed=True)
        (local_reports / f"changes-{label}.xlsx").write_bytes(workbook_bytes(review))
    page.get_by_text("What changed?", exact=True).click()
    page.get_by_role("heading", name="What changed?", exact=True).wait_for()
    page.locator('input[type=file]').nth(0).set_input_files("reports/changes-earlier.xlsx")
    page.locator('input[type=file]').nth(1).set_input_files("reports/changes-latest.xlsx")
    with page.expect_download() as change_item:
        page.get_by_role("button", name="Download change review", exact=True).click()
    change_item.value.save_as("reports/changes-review.xlsx")
    change_book = load_workbook("reports/changes-review.xlsx", read_only=True, data_only=True)
    values = list(change_book["Changes"].values)
    changed = dict(zip(values[0], values[1]))
    assert changed["profit_change"] == -10
    assert changed["cogs_change"] == 10
    assert changed["decision_ready"] is False
    assert len(list(change_book["Sources"].values)) == 3
    change_book.close()
    print("Two-report comparison browser download reconciled")
    browser.close()

