from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook

from marketprice.actuals import reconcile
from marketprice.digikala import _jalali_to_gregorian, review_digikala_invoice

HEADERS = [
    "کد", "تاریخ", "کد تنوع", "عنوان تنوع", "شماره سفارش", "سریال",
    "بستانکار (﷼)", "بدهکار (﷼)", "تخفیف بستانکار (﷼)",
    "تخفیف بدهکار (﷼)", "مبلغ نهایی بستانکار (﷼)",
    "مبلغ نهایی بدهکار (﷼)", "توضیحات",
]


def native_invoice(*, formula=False, payable=229430):
    book = Workbook()
    summary = book.active
    summary.title = "صورت حساب"
    summary.append(["نوع", "عنوان", "توضیحات", "تعداد", "مبلغ محاسبه شده", "",
                    "تخفیف محاسبه شده", "", "تخفیف درصدی", "مبلغ نهایی", ""])
    summary.append(["", "", "", "", "بدهکار (ریال)", "بستانکار (ریال)",
                    "بدهکار (ریال)", "بستانکار (ریال)", "", "بدهکار (ریال)", "بستانکار (ریال)"])
    lines = [
        ("فروش", "فروش", 1, 0, 100000),
        ("فروش", "فروش اعتباری", 1, 0, 200000),
        ("کمیسیون", "کمیسیون فروش", 1, 12000, 0),
        ("کمیسیون", "کمیسیون فروش اعتباری", 1, 24000, 0),
        ("کمیسیون", "درآمد توسعه پلتفرم", 1, 6600, 0),
        ("هزینه معاف از مالیات بر ارزش افزوده", "هزینه حمل از/به فروشنده", 1, 1000, 0),
        ("هزینه", "هزینه پرینت لیبل در ورودی انبار", 1, 600, 0),
        ("هزینه", "هزینه پردازش", 1, 3500, 0),
        ("هزینه معاف از مالیات بر ارزش افزوده", "هزینه ارسال", 1, 3500, 0),
        ("هزینه", "هزینه پردازش اعتباری", 1, 7000, 0),
        ("هزینه معاف از مالیات بر ارزش افزوده", "هزینه ارسال اعتباری", 1, 7000, 0),
    ]
    for kind, title, count, debit, credit in lines:
        summary.append([kind, title, title, count, debit, credit, 0, 0, 0, debit, credit])
    summary.append([])
    summary.append([])
    summary.append([None, None, None, "عنوان", "مبلغ نهایی"])
    summary.append([None, None, None, None, "بدهکار (ریال)", "بستانکار (ریال)"])
    for title, debit, credit in [
        ("فروش", 0, 300000), ("کمیسیون", 42600, 0), ("هزینه", 11100, 0),
        ("هزینه معاف از مالیات بر ارزش افزوده", 11500, 0),
        ("ارزش افزوده 9 % ", 5370, 0), ("مبلغ قابل پرداخت", 0, payable),
    ]:
        summary.append([None, None, None, title, debit, credit])

    def sheet(name, rows, compact=False):
        ws = book.create_sheet(name)
        if compact:
            ws.append(["کد", "تاریخ", "بستانکار (﷼)", "بدهکار (﷼)",
                       "تخفیف بستانکار (﷼)", "تخفیف بدهکار (﷼)",
                       "مبلغ نهایی بستانکار (﷼)", "مبلغ نهایی بدهکار (﷼)", "توضیحات"])
        else:
            ws.append(HEADERS)
        for row in rows:
            ws.append(row)
        return ws

    date = "۱۴۰۴/۱۲/۰۴ ۱۰:۰۰"
    regular = ["1", date, "SKU-1", "Synthetic", "O-1", "S-1"]
    credit = ["2", date, "SKU-1", "Synthetic", "O-2", "S-2"]
    sheet("فروش", [regular + [100000, 0, 0, 0, 100000, 0, "sale"]])
    sheet("فروش اعتباری", [credit + [200000, 0, 0, 0, 200000, 0, "sale"]])
    sheet("کمیسیون فروش", [["3", date, "SKU-1", "Synthetic", "O-1", "S-1", 0, 12000, 0, 0, 0, 12000, "12%"]])
    sheet("کمیسیون فروش اعتباری", [["4", date, "SKU-1", "Synthetic", "O-2", "S-2", 0, 24000, 0, 0, 0, 24000, "12%"]])
    sheet("درآمد توسعه پلتفرم", [["5", date, "SKU-1", "Synthetic", "O-2", "S-2", 0, 6600, 0, 0, 0, 6600, "3.3%"]])
    sheet("هزینه حمل از - به فروشنده", [["6", date, 0, 1000, 0, 0, 0, 1000, "shipment"]], compact=True)
    sheet("هزینه پرینت لیبل در ورودی انب", [["7", date, 0, 600, 0, 0, 0, 600, "label"]], compact=True)
    for name, row, amount in [
        ("هزینه پردازش", regular, 3500), ("هزینه ارسال", regular, 3500),
        ("هزینه پردازش اعتباری", credit, 7000), ("هزینه ارسال اعتباری", credit, 7000),
    ]:
        sheet(name, [[name, date, "SKU-1", "Synthetic", row[4], row[5], 0, amount, 0, 0, 0, amount, "3.5%"]])
    if formula:
        summary["J3"] = "=1+1"
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


def test_native_invoice_reconciles_and_keeps_unallocated_charges_visible():
    result = review_digikala_invoice(native_invoice(), "invoice.xlsx")
    reconciliation = result["Invoice_Reconciliation"][0]
    assert reconciliation["status"] == "MATCHED"
    assert reconciliation["difference"] == 0
    assert reconciliation["invoice_payable"] == 229430
    tax = result["Tax_Check"][0]
    assert tax == {
        "taxable_base": 53700,
        "invoice_tax": 5370,
        "label_rate_percent": 9,
        "label_rate_expected_tax": 4833,
        "observed_exact_rate_percent": 10,
        "observed_method": "floor each taxable summary line",
        "label_mismatch": True,
        "difference_from_label": 537,
    }
    rules = {(r["charge"], r["payment_type"]): r["observed_rate"] for r in result["Observed_Rules"]}
    assert rules[("کمیسیون فروش", "cash")] == Decimal("0.12")
    assert rules[("درآمد توسعه پلتفرم", "credit")] == Decimal("0.033")
    assert rules[("هزینه ارسال", "cash")] == Decimal("0.035")
    assert rules[("هزینه پردازش اعتباری", "credit")] == Decimal("0.035")
    orders = {row["order_id"]: row for row in result["Order_Net_Before_Cost"]}
    assert orders["O-1"]["fees_before_unallocated_tax"] == 19000
    assert orders["O-2"]["fees_before_unallocated_tax"] == 44600
    assert sum(row["amount"] for row in result["Unallocated_Charges"]) == 6970
    assert result["Errors"] == []
    actuals = reconcile(
        result["Normalized_Transactions"],
        [{
            "sku": "SKU-1", "currency": "IRR", "effective_date": "2025-01-01",
            "historical_unit_cost": 50000, "replacement_unit_cost": 55000, "source": "synthetic",
        }],
        as_of=date(2026, 2, 23),
    )
    assert actuals["Errors"] == []
    assert actuals["Platform_Comparison"][0]["units_sold"] == 2


def test_native_invoice_reports_reconciliation_difference_and_rejects_formulas():
    result = review_digikala_invoice(native_invoice(payable=229400), "invoice.xlsx")
    assert result["Invoice_Reconciliation"][0]["status"] == "REVIEW"
    assert result["Invoice_Reconciliation"][0]["difference"] == 30
    with pytest.raises(ValueError, match="DIGIKALA_FORMULA"):
        review_digikala_invoice(native_invoice(formula=True), "invoice.xlsx")


def test_jalali_conversion_and_file_guards():
    assert _jalali_to_gregorian("۱۴۰۴/۰۱/۰۱").isoformat() == "2025-03-21"
    assert _jalali_to_gregorian("۱۴۰۵/۰۸/۱۳").isoformat() == "2026-11-04"
    with pytest.raises(ValueError, match="DIGIKALA_FILE_TYPE"):
        review_digikala_invoice(b"x", "invoice.csv")
