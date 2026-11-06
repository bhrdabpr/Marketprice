"""Read a native Digikala invoice export and preserve what the file can prove.

The adapter derives observed rates from the invoice.  It does not install a
universal Digikala fee table, allocate account-level charges to products, or
treat an invoice's payable amount as evidence that cash was paid.
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from collections import defaultdict
from datetime import date as Date
from decimal import ROUND_FLOOR, Decimal

from openpyxl import load_workbook

from .io import MAX_ROWS, MAX_XLSX_BYTES
from .precision import financial

D = Decimal
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _number(value) -> Decimal:
    raw = _text(value).translate(PERSIAN_DIGITS)
    raw = raw.replace("٬", "").replace(",", "").replace("٫", ".").replace("﷼", "")
    if not raw:
        return D(0)
    return D(raw)


def _jalali_to_gregorian(value) -> Date:
    match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", _text(value).translate(PERSIAN_DIGITS))
    if not match:
        raise ValueError("Invalid Jalali date")
    jy, jm, jd = map(int, match.groups())
    if not (1 <= jm <= 12 and 1 <= jd <= 31):
        raise ValueError("Invalid Jalali date")
    jy += 1595
    days = -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33 + 3) // 4) + jd
    days += (jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    month_days = [0, 31, 29 if gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0) else 28,
                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > month_days[gm]:
        gd -= month_days[gm]
        gm += 1
    return Date(gy, gm, gd)


def _safe_book(content: bytes):
    if not content or len(content) > MAX_XLSX_BYTES:
        raise ValueError("DIGIKALA_FILE_SIZE: provide an XLSX up to 50 MiB")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > 2000 or sum(i.file_size for i in infos) > 500 * 1024 * 1024:
                raise ValueError("DIGIKALA_UNSAFE_WORKBOOK: decompression budget exceeded")
            if any("vbaproject" in i.filename.lower() or "externallinks/" in i.filename.lower()
                   for i in infos):
                raise ValueError("DIGIKALA_UNSAFE_WORKBOOK: macros/external links forbidden")
        return load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("DIGIKALA_INVALID_FILE: malformed XLSX") from exc


def _rows(sheet, columns: int) -> list[tuple]:
    rows = []
    empty_run = 0
    for row_number, row in enumerate(
        sheet.iter_rows(min_row=1, max_row=MAX_ROWS + 1, min_col=1, max_col=columns), 1
    ):
        if any(cell.data_type == "f" for cell in row):
            raise ValueError(f"DIGIKALA_FORMULA: formula found in {sheet.title} row {row_number}")
        values = tuple(cell.value for cell in row)
        if all(value is None or _text(value) == "" for value in values):
            empty_run += 1
            if empty_run >= 20:
                break
            continue
        empty_run = 0
        rows.append(values)
    if len(rows) > MAX_ROWS:
        raise ValueError("DIGIKALA_TOO_MANY_ROWS")
    return rows


def _summary(rows: list[tuple]) -> tuple[list[dict], dict[str, Decimal], int | None]:
    lines, totals, label_rate = [], {}, None
    for source_row, row in enumerate(rows, 1):
        title = _text(row[1]) if len(row) > 1 else ""
        kind = _text(row[0]) if row else ""
        if source_row >= 3 and title and kind:
            lines.append(
                {
                    "source_row": source_row,
                    "type": kind,
                    "title": title,
                    "count": _number(row[3]),
                    "final_debit": _number(row[9]),
                    "final_credit": _number(row[10]),
                }
            )
        total_title = _text(row[3]) if len(row) > 3 else ""
        if source_row >= 16 and total_title:
            totals[total_title] = _number(row[5]) - _number(row[4])
            rate_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", total_title.translate(PERSIAN_DIGITS))
            if "ارزش افزوده" in total_title and rate_match:
                label_rate = int(D(rate_match.group(1)))
    return lines, totals, label_rate


def _detail(sheet_name: str, rows: list[tuple], settlement_id: str) -> tuple[list[dict], list[dict]]:
    if not rows:
        return [], []
    headers = [_text(value) for value in rows[0]]
    positions = {header: index for index, header in enumerate(headers)}
    credit_i = next((i for i, h in enumerate(headers) if "مبلغ نهایی بستانکار" in h), None)
    debit_i = next((i for i, h in enumerate(headers) if "مبلغ نهایی بدهکار" in h), None)
    if credit_i is None or debit_i is None:
        return [], [{"sheet": sheet_name, "row": 1, "error": "FINAL_AMOUNT_COLUMNS_MISSING"}]
    is_sale = sheet_name in {"فروش", "فروش اعتباری"}
    payment_type = "credit" if "اعتباری" in sheet_name else ("cash" if is_sale else "unknown")
    records, errors = [], []
    for source_row, row in enumerate(rows[1:], 2):
        try:
            code = _text(row[positions.get("کد", 0)])
            if not code:
                continue
            amount = _number(row[credit_i]) - _number(row[debit_i])
            date_value = row[positions["تاریخ"]]
            order_id = _text(row[positions["شماره سفارش"]]) if "شماره سفارش" in positions else ""
            sku = _text(row[positions["کد تنوع"]]) if "کد تنوع" in positions else ""
            records.append(
                {
                    "transaction_id": code,
                    "marketplace": "digikala",
                    "currency": "IRR",
                    "date": _jalali_to_gregorian(date_value).isoformat(),
                    "kind": "sale" if is_sale else "fee",
                    "amount": amount,
                    "order_id": order_id,
                    "sku": sku,
                    "settlement_id": settlement_id,
                    "quantity": D(1) if is_sale else D(0),
                    "payment_type": payment_type,
                    "source_sheet": sheet_name,
                    "source_row": source_row,
                    "description": _text(row[positions["توضیحات"]]) if "توضیحات" in positions else "",
                }
            )
        except (KeyError, IndexError, ValueError, ArithmeticError) as exc:
            errors.append({"sheet": sheet_name, "row": source_row, "error": str(exc)[:500]})
    return records, errors


def _tax_check(lines: list[dict], totals: dict[str, Decimal], label_rate: int | None) -> dict:
    tax_key = next((key for key in totals if key.strip().startswith("ارزش افزوده")), "")
    actual = -totals.get(tax_key, D(0))
    taxable = [line for line in lines if line["type"] in {"کمیسیون", "هزینه"}]
    base = sum((line["final_debit"] for line in taxable), D(0))
    exact = []
    for percent in range(1, 26):
        expected = sum(
            (line["final_debit"] * D(percent) / 100).to_integral_value(rounding=ROUND_FLOOR)
            for line in taxable
        )
        if expected == actual:
            exact.append(percent)
    observed = exact[0] if len(exact) == 1 else None
    label_expected = (
        sum(
            (line["final_debit"] * D(label_rate) / 100).to_integral_value(rounding=ROUND_FLOOR)
            for line in taxable
        )
        if label_rate is not None else None
    )
    return {
        "taxable_base": base,
        "invoice_tax": actual,
        "label_rate_percent": label_rate,
        "label_rate_expected_tax": label_expected,
        "observed_exact_rate_percent": observed,
        "observed_method": "floor each taxable summary line" if observed is not None else "unresolved",
        "label_mismatch": bool(observed is not None and label_rate != observed),
        "difference_from_label": actual - label_expected if label_expected is not None else None,
    }


@financial
def review_digikala_invoice(content: bytes, filename: str = "invoice.xlsx") -> dict[str, list[dict]]:
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("DIGIKALA_FILE_TYPE: use the native XLSX invoice export")
    book = _safe_book(content)
    try:
        if "صورت حساب" not in book.sheetnames:
            raise ValueError("DIGIKALA_TEMPLATE: 'صورت حساب' sheet is missing")
        summary_lines, totals, label_rate = _summary(_rows(book["صورت حساب"], 11))
        if not summary_lines or "مبلغ قابل پرداخت" not in totals:
            raise ValueError("DIGIKALA_TEMPLATE: summary rows are missing")
        statement_id = "dk-" + hashlib.sha256(content).hexdigest()[:16]
        transactions, errors = [], []
        for sheet in book.worksheets:
            if sheet.title == "صورت حساب":
                continue
            detail, sheet_errors = _detail(sheet.title, _rows(sheet, 13), statement_id)
            transactions.extend(detail)
            errors.extend(sheet_errors)
    finally:
        book.close()

    tax = _tax_check(summary_lines, totals, label_rate)
    latest = max((record["date"] for record in transactions), default=Date.today().isoformat())
    if tax["invoice_tax"]:
        transactions.append(
            {
                "transaction_id": statement_id + "-summary-tax",
                "marketplace": "digikala",
                "currency": "IRR",
                "date": latest,
                "kind": "tax",
                "amount": -tax["invoice_tax"],
                "order_id": "",
                "sku": "",
                "settlement_id": statement_id,
                "quantity": D(0),
                "payment_type": "unknown",
                "source_sheet": "صورت حساب",
                "source_row": next(
                    (line["source_row"] for line in summary_lines if "ارزش افزوده" in line["title"]),
                    "summary total",
                ),
                "description": "Aggregate invoice VAT; not allocated to orders because the export has no tax detail rows.",
            }
        )

    detail_credit = sum((r["amount"] for r in transactions if r["kind"] == "sale"), D(0))
    detail_debit = -sum((r["amount"] for r in transactions if r["kind"] in {"fee", "tax"}), D(0))
    payable = totals["مبلغ قابل پرداخت"]
    recomputed = detail_credit - detail_debit
    summary_debit = sum((line["final_debit"] for line in summary_lines), D(0)) + tax["invoice_tax"]
    summary_credit = sum((line["final_credit"] for line in summary_lines), D(0))

    sale_by_order = {r["order_id"]: r for r in transactions if r["kind"] == "sale" and r["order_id"]}
    fees_by_order: dict[str, list[dict]] = defaultdict(list)
    for record in transactions:
        if record["kind"] == "fee" and record["order_id"]:
            fees_by_order[record["order_id"]].append(record)
    orders = []
    for order_id, sale in sorted(sale_by_order.items()):
        fees = fees_by_order.get(order_id, [])
        fee_total = -sum((r["amount"] for r in fees), D(0))
        orders.append(
            {
                "order_id": order_id,
                "sku": sale["sku"],
                "payment_type": sale["payment_type"],
                "sale": sale["amount"],
                "fees_before_unallocated_tax": fee_total,
                "fee_rate": fee_total / sale["amount"] if sale["amount"] else None,
                "net_before_unallocated_tax_and_purchase_cost": sale["amount"] - fee_total,
                "fee_rows": len(fees),
            }
        )

    rule_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in transactions:
        if record["kind"] == "fee" and record["order_id"] in sale_by_order:
            payment_type = sale_by_order[record["order_id"]]["payment_type"]
            rule_groups[(record["source_sheet"], payment_type)].append(record)
    rules = []
    for (source_sheet, payment_type), records in sorted(rule_groups.items()):
        bases = [sale_by_order[r["order_id"]]["amount"] for r in records]
        rates = [(-r["amount"] / base) for r, base in zip(records, bases, strict=True) if base]
        same_rate = bool(rates) and max(rates) - min(rates) <= D("0.0000001")
        rules.append(
            {
                "charge": source_sheet,
                "payment_type": payment_type,
                "observations": len(records),
                "observed_rate": rates[0] if same_rate else None,
                "basis": "sale amount" if same_rate else "not established",
                "status": "OBSERVED_THIS_FILE" if same_rate else "REVIEW",
            }
        )

    unallocated = []
    for record in transactions:
        if record["kind"] in {"fee", "tax"} and not record["order_id"]:
            unallocated.append(
                {
                    "charge": record["source_sheet"],
                    "source_row": record["source_row"],
                    "amount": -record["amount"],
                    "reason": "No order or SKU key in the native export",
                }
            )
    normalized_fields = {
        "transaction_id", "marketplace", "currency", "date", "kind", "amount", "order_id",
        "sku", "settlement_id", "quantity", "payment_type",
    }
    normalized = [{key: value for key, value in record.items() if key in normalized_fields}
                  for record in transactions]
    return {
        "Invoice_Reconciliation": [
            {
                "currency": "IRR",
                "summary_credit": summary_credit,
                "detail_credit": detail_credit,
                "summary_debit_including_tax": summary_debit,
                "detail_debit_including_tax": detail_debit,
                "invoice_payable": payable,
                "recomputed_payable": recomputed,
                "difference": recomputed - payable,
                "status": "MATCHED" if recomputed == payable and summary_credit == detail_credit
                and summary_debit == detail_debit and not errors else "REVIEW",
                "statement_id": statement_id,
            }
        ],
        "Tax_Check": [tax],
        "Observed_Rules": rules,
        "Order_Net_Before_Cost": orders,
        "Unallocated_Charges": unallocated,
        "Normalized_Transactions": normalized,
        "Transaction_Evidence": transactions,
        "Source_Summary": summary_lines,
        "Errors": errors,
        "Assumptions": [
            {
                "scope": "Observed native invoice only",
                "currency": "IRR",
                "sale_quantity": "One unit per native sale line; verify if a future export includes quantities.",
                "tax_allocation": "Aggregate VAT remains unallocated because the export has no order-level VAT rows.",
                "payment": "Invoice payable is expected receivable, not proof of bank payment.",
                "rule_policy": "Observed rates are evidence for this file, not a universal Digikala contract table.",
            }
        ],
    }
