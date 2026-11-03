"""Bounded import and formula-free, literal-text workbook export."""

import csv
import io
import json
import zipfile
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .validation import normalize_headers

MAX_BYTES = 25 * 1024 * 1024
MAX_XLSX_BYTES = 50 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLS = 80


def read_upload(
    content: bytes,
    filename: str,
    mapping: dict | None = None,
    *,
    preserve_headers: bool = False,
    encoding: str = "utf-8-sig",
    sheet_name: str | None = None,
    cached_values: bool = False,
) -> list[dict]:
    suffix = Path(filename).suffix.lower()
    budget = MAX_XLSX_BYTES if suffix == ".xlsx" else MAX_BYTES
    if len(content) > budget:
        raise ValueError("FILE_TOO_LARGE: maximum 50 MiB XLSX / 25 MiB CSV")
    try:
        if suffix == ".csv":
            if encoding not in {"utf-8-sig", "utf-16", "cp1256", "cp1252"}:
                raise ValueError("UNSUPPORTED_ENCODING")
            source = csv.reader(io.StringIO(content.decode(encoding)))
            return _rows(source, mapping, preserve_headers)
        if suffix != ".xlsx":
            raise ValueError("UNSUPPORTED_FILE: use .csv or .xlsx")
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > 2000 or sum(i.file_size for i in infos) > 500 * 1024 * 1024:
                raise ValueError("UNSAFE_WORKBOOK: decompression budget exceeded")
            if any(
                "vbaproject" in i.filename.lower()
                or (not cached_values and "externallinks/" in i.filename.lower())
                for i in infos
            ):
                raise ValueError("UNSAFE_WORKBOOK: macros/external links forbidden")
        names = workbook_sheets(content)
        chosen = sheet_name or ("Products" if "Products" in names else names[0])
        import posixpath
        from xml.etree import ElementTree as ET

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for name in ("xl/workbook.xml", "xl/_rels/workbook.xml.rels"):
                if archive.getinfo(name).file_size > 1024 * 1024:
                    raise ValueError("UNSAFE_WORKBOOK: metadata exceeds budget")
            root = ET.fromstring(archive.read("xl/workbook.xml"))
            rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            rel_id = next(
                s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                for s in root.findall("{*}sheets/{*}sheet")
                if s.attrib["name"] == chosen
            )
            target = next(r.attrib["Target"] for r in rels if r.attrib["Id"] == rel_id)
            member = (
                target.lstrip("/")
                if target.startswith("/")
                else posixpath.normpath(posixpath.join("xl", target))
            )
            if archive.getinfo(member).file_size > 200 * 1024 * 1024:
                raise ValueError(
                    "WORKSHEET_TOO_LARGE: selected sheet expands beyond 200 MiB; save a values-only copy without unused formatted rows"
                )
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=cached_values, keep_links=False)
        try:
            sheet = (
                book[sheet_name]
                if sheet_name
                else (book["Products"] if "Products" in book.sheetnames else book.worksheets[0])
            )
            # Ignore unreliable stored dimensions; bounded iteration below is authoritative.
            sheet.reset_dimensions()
            return _rows(sheet.iter_rows(values_only=True), mapping, preserve_headers)
        finally:
            book.close()
    except (ValueError, UnicodeError, zipfile.BadZipFile, KeyError, OSError) as exc:
        raise ValueError(f"INVALID_FILE: {exc}") from exc
    except Exception as exc:
        raise ValueError("INVALID_FILE: malformed or unsupported workbook") from exc


def _rows(source, mapping, preserve_headers):
    original = list(next(source, []))
    if preserve_headers:
        original = [
            h if h is not None and str(h).strip() else f"Unnamed column {i}"
            for i, h in enumerate(original, 1)
        ]
    headers = normalize_headers(original, {str(h): str(h) for h in original} if preserve_headers else mapping)
    if not headers or len(headers) > MAX_COLS or any(not h or h == "None" for h in headers):
        raise ValueError("INVALID_HEADERS")
    rows: list[dict] = []
    pending_empty = 0
    for rownum, values in enumerate(source, 2):
        if all(v is None or v == "" for v in values):
            pending_empty += 1
            continue
        if rownum > MAX_ROWS + 1:
            raise ValueError("TOO_MANY_ROWS: use batches of at most 100000")
        if len(values) > len(headers):
            if not preserve_headers or len(values) > MAX_COLS:
                raise ValueError(f"EXTRA_COLUMNS at row {rownum}")
            extra = [f"Unnamed column {i}" for i in range(len(headers) + 1, len(values) + 1)]
            if set(extra) & set(headers):
                raise ValueError("INVALID_HEADERS: unnamed columns conflict with existing headers")
            headers.extend(extra)
            for previous in rows:
                previous.update(dict.fromkeys(extra))
        if any(isinstance(v, str) and len(v) > 16000 for v in values):
            raise ValueError("CELL_TOO_LONG")
        record = dict(zip(headers, list(values) + [None] * (len(headers) - len(values))))
        if len(json.dumps(record, default=str, ensure_ascii=False)) > 30000:
            raise ValueError("ROW_TOO_LARGE: audit cell must preserve all original values")
        if pending_empty:
            rows.extend(dict.fromkeys(headers) for _ in range(pending_empty))
            pending_empty = 0
        rows.append(record)
    if not rows:
        raise ValueError("EMPTY_FILE")
    return rows


def json_default(value):
    return str(value) if isinstance(value, Decimal) else value


def literal_cell(ws, value, header=False):
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, default=json_default, ensure_ascii=False, sort_keys=True)
    cell = WriteOnlyCell(ws, value=value)
    if isinstance(value, str):
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.data_type = "s"  # Never execute user text beginning =, +, -, @ or whitespace.
    if isinstance(value, Decimal):
        # Preserve exact precision beyond Excel's 15 significant digits as literal text.
        if len(value.as_tuple().digits) > 15:
            cell.value, cell.data_type = str(value), "s"
        else:
            cell.number_format = "#,##0.00########;[Red](#,##0.00########);–"
    if header:
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="173B4F")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    return cell


def workbook_bytes(sheets: dict[str, list[dict]]) -> bytes:
    book = Workbook(write_only=True)
    for name, records in sheets.items():
        ws = book.create_sheet(name)
        ws.freeze_panes = "C2"
        headers = list(dict.fromkeys(k for r in records for k in r)) or ["status"]
        for i, h in enumerate(headers, 1):
            ws.column_dimensions[get_column_letter(i)].width = min(42, max(18, len(h) + 3))
        ws.row_dimensions[1].height = 32
        ws.append([literal_cell(ws, h, True) for h in headers])
        for record in records:
            ws.append([literal_cell(ws, record.get(h)) for h in headers])
        if records:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(records) + 1}"
        else:
            ws.append([literal_cell(ws, "No records")])
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def pricing_summary_csv(result: dict[str, list[dict]]) -> bytes:
    """Compact decision export; omit original merchant columns and technical audit payloads."""
    fields = [
        "row",
        "sku",
        "currency",
        "status",
        "current_price",
        "break_even",
        "target_margin",
        "margin_floor",
        "normal_price",
        "profit",
        "actual_margin",
        "action",
        "decision_ready",
        "problem_fields",
    ]
    records = [{**r, "status": "VALID"} for r in result.get("Price_Analysis", [])]
    problems: dict[int, list[str]] = {}
    for error in result.get("Errors", []):
        problems.setdefault(error["row"], []).append(str(error.get("field", "")))
    for row in result.get("Product_Calculations", []):
        if row.get("status") == "INVALID":
            records.append({**row, "problem_fields": "; ".join(dict.fromkeys(problems.get(row["row"], [])))})
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(fields)
    for record in records:
        values = []
        for field in fields:
            value = record.get(field)
            text = "" if value is None else str(value)
            if isinstance(value, str) and text.lstrip().startswith(("=", "+", "-", "@")):
                text = "'" + text
            values.append(text)
        writer.writerow(values)
    return stream.getvalue().encode("utf-8-sig")


def workbook_sheets(content: bytes) -> list[str]:
    """Read bounded workbook metadata without evaluating formulas or resolving links."""
    from xml.etree import ElementTree as ET

    if len(content) > MAX_XLSX_BYTES:
        raise ValueError("FILE_TOO_LARGE: maximum 50 MiB XLSX")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            info = archive.getinfo("xl/workbook.xml")
            if info.file_size > 1024 * 1024:
                raise ValueError("UNSAFE_WORKBOOK: metadata exceeds budget")
            root = ET.fromstring(archive.read(info))
            return [s.attrib["name"] for s in root.findall("{*}sheets/{*}sheet")]
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError("INVALID_FILE: workbook metadata cannot be read") from exc
