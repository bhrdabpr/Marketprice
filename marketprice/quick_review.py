"""File-to-answer workflows. Preserve the input and explain incomplete results."""

import csv
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from .flexible import calculate_catalog
from .importing import IGNORE, UNMAPPED, header_key, map_rows, suggest_mapping
from .io import read_upload
from .listings import map_listing_rows, review_listings, suggest_listing_mapping
from .models import CURRENCIES
from .precision import financial
from .validation import number

TASKS = ("pricing", "profit", "campaign", "storage", "listing")
COLUMNS = {
    "impressions": ("impressions", "نمایش"),
    "clicks": ("clicks", "کلیک"),
    "orders": ("attributed orders", "7 day total orders (#)", "سفارش منتسب"),
    "spend": ("spend", "ad spend", "هزینه تبلیغات"),
    "sales": ("attributed sales", "attributed revenue", "7 day total sales"),
    "profit": ("net profit", "سود خالص"),
    "investment": ("invested capital", "total investment", "سرمایه گذاری"),
    "units": ("units stored", "stored units", "تعداد انبار"),
    "fee": ("monthly storage fee per unit", "storage fee per unit per month"),
    "months": ("months stored", "storage months"),
}


def file_rows(content, filename, sheet=None):
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        if len(content) > 3 * 1024**2:
            raise ValueError("Use a text PDF under 3 MB or upload the spreadsheet.")
        try:
            pdf = PdfReader(BytesIO(content))
            if pdf.is_encrypted or len(pdf.pages) > 20:
                raise ValueError
            lines = "\n".join((p.extract_text() or "") for p in pdf.pages).splitlines()
        except Exception as exc:
            raise ValueError("Upload a readable text PDF or the original spreadsheet.") from exc
        lines = [line for line in lines if line.strip()]
        if not lines or not any(c in lines[0] for c in (",", ";", "\t")):
            raise ValueError("This PDF has no clearly separated table. Upload the original Excel or CSV file.")
        content = "\n".join(lines).encode()
        filename = "table.csv"
    delimiter = ","
    if filename.lower().endswith(".csv"):
        sample = content[:64000].decode("utf-8-sig", errors="ignore")
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
        except csv.Error:
            pass
    return read_upload(content, filename, preserve_headers=True, delimiter=delimiter, sheet_name=sheet)


def mapped_values(row):
    values = {}
    for header, value in row.items():
        key = header_key(str(header))
        if key in values:
            raise ValueError(f"Two columns have the same meaning: {header}")
        values[key] = value
    return values


@financial
def metrics(task, row, index):
    values = mapped_values(row)
    out = {"Row": index, "SKU": values.get("sku", values.get("asin", ""))}
    missing = []
    invalid = []

    def get(field):
        aliases = [alias for alias in COLUMNS[field] if alias in values]
        if len(aliases) > 1:
            invalid.append(f"Choose one {COLUMNS[field][0]} column")
            return None
        value = values.get(aliases[0]) if aliases else None
        if value is None or str(value).strip() == "":
            missing.append(COLUMNS[field][0])
            return None
        try:
            if "%" in str(value).replace("٪", "%"):
                raise ValueError
            n = number(value)
            if abs(n) > Decimal("1e18") or (field != "profit" and n < 0):
                raise ValueError
            if field in {"clicks", "orders", "impressions", "units"} and n != n.to_integral_value():
                raise ValueError
            return n
        except (ValueError, ArithmeticError):
            invalid.append(f"Check {aliases[0]} on row {index}")
            return None

    def ratio(label, numerator, denominator, factor=1):
        if numerator is None or denominator is None:
            return
        if not denominator:
            invalid.append(f"{label} has a zero denominator")
            return
        out[label] = round(numerator / denominator * factor, 4)

    currency = str(values.get("currency") or values.get("ارز") or "").upper()
    if task == "campaign":
        clicks, impressions, orders, spend, sales = (get(k) for k in ("clicks", "impressions", "orders", "spend", "sales"))
        if clicks is not None and impressions is not None and clicks > impressions:
            invalid.append("Clicks exceed impressions. Check the reporting period")
        else:
            ratio("CTR (%)", clicks, impressions, 100)
        ratio("Orders per click (%)", orders, clicks, 100)
        ratio("ROAS (×)", sales, spend)
        if currency in CURRENCIES:
            out["Currency"] = currency
            ratio("Cost per attributed order", spend, orders)
        elif spend is not None:
            missing.append("currency")
    elif task == "storage":
        units, fee, months = (get(k) for k in ("units", "fee", "months"))
        if currency not in CURRENCIES:
            missing.append("currency")
        elif units is not None and fee is not None and months is not None:
            out.update({"Storage cost": units * fee * months, "Currency": currency})
    return out | {"Next input": ", ".join(dict.fromkeys(missing)), "Check": ". ".join(invalid)}


@financial
def price_report(rows, task):
    headers = list(rows[0])
    mapping = suggest_mapping(headers)
    for h in headers:
        if mapping[h] in {IGNORE, UNMAPPED}:
            field = {"fba fee per unit": "fulfillment", "fulfillment fee per unit": "fulfillment",
                     "purchase cost per unit": "purchase_cost"}.get(header_key(h))
            if field:
                mapping[h] = field
    selected = {k: v for k, v in mapping.items() if v not in {IGNORE, UNMAPPED}}
    entries = []
    checks = []
    confidence = []
    if "purchase_cost" in selected.values() and "currency" in selected.values():
        mapped = map_rows(rows, {k: selected.get(k, IGNORE) for k in headers})
        for record in mapped:
            for field in ("purchase_cost", "current_price", "fulfillment", "shipping", "packaging", "warehouse"):
                if "%" in str(record.get(field, "")).replace("٪", "%"):
                    record[field] = "Expected a monetary amount"
        result = calculate_catalog(mapped, currency="USD", target_margin="0", discounts=[], events=[])
        confidence = result["Cost_Confidence"]
        for record in result["Product_Calculations"]:
            entries.append({k: record[k] for k in (
                "sku", "currency", "profit", "cost_confidence", "current_price_status"
            ) if k in record})
        if task == "pricing":
            entries = [{k: r.get(k) for k in ("sku", "currency", "current_price", "margin_floor", "target_margin", "cost_confidence")}
                       for r in result["Price_Analysis"]]
        checks.extend(result["Errors"])
    else:
        checks.append({"Next input": "Add purchase_cost and currency columns for per-unit prices and contribution."})
    if task == "profit":
        for i, raw in enumerate(rows):
            values = mapped_values(raw)
            entry = entries[i] if i < len(entries) else {}
            if i >= len(entries):
                entries.append(entry)
            entry["Row"] = i + 2
            entry.setdefault("sku", values.get("sku") or values.get("asin", ""))
            for label, field in (("Net profit", "profit"), ("Invested capital", "investment")):
                matches = [values[k] for k in COLUMNS[field] if k in values]
                if len(matches) == 1:
                    try:
                        if "%" in str(matches[0]).replace("٪", "%"):
                            raise ValueError
                        entry[label] = number(matches[0])
                    except ValueError:
                        checks.append({"Row": i+2, "Check": f"Invalid {label.lower()}"})
            if "Net profit" in entry and entry.get("Invested capital", 0) > 0:
                entry["ROI (%)"] = round(100 * entry["Net profit"] / entry["Invested capital"], 4)
            else:
                entry["For ROI"] = "Supply net profit and positive invested capital for the same period and currency."
            price_key = next((k for k, v in selected.items() if v == "current_price"), "")
            cost_key = next((k for k, v in selected.items() if v == "purchase_cost"), "")
            try:
                price_value, cost_value = raw.get(price_key), raw.get(cost_key)
                if any("%" in str(v).replace("٪", "%") for v in (price_value, cost_value)):
                    raise ValueError
                price, cost = number(price_value), number(cost_value)
                if price > 0 and cost >= 0:
                    entry["Gross margin (%)"] = round(100 * (price - cost) / price, 4)
                if cost > 0 and price >= 0:
                    entry["Markup on purchase cost (%)"] = round(100 * (price - cost) / cost, 4)
            except ValueError:
                pass
    ignored = [k for k in headers if k not in selected]
    return {"Answers": entries, "Checks": checks, "Cost details": confidence, "Columns outside price calculation": [{"Column": h} for h in ignored]}


def analyze(task, rows):
    if not rows or len(rows) > 10000:
        raise ValueError("Use a file with 1 to 10,000 rows in quick review.")
    if task == "listing":
        mapping = suggest_listing_mapping(rows[0])
        for h in mapping:
            if header_key(h) == "asin" and "sku" not in mapping.values():
                mapping[h] = "sku"
        return review_listings(map_listing_rows(rows, mapping))
    if task in ("pricing", "profit"):
        return price_report(rows, task)
    if task in ("campaign", "storage"):
        return {"Answers": [metrics(task, row, i) for i, row in enumerate(rows, 2)]}
    raise ValueError("Unknown service")
