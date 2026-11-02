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
MAX_ROWS = 100_000
MAX_COLS = 80


def read_upload(content: bytes, filename: str, mapping: dict | None = None) -> list[dict]:
    if len(content) > MAX_BYTES:
        raise ValueError("FILE_TOO_LARGE: maximum 25 MiB")
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".csv":
            source = csv.reader(io.StringIO(content.decode("utf-8-sig")))
            return _rows(source, mapping)
        if suffix != ".xlsx":
            raise ValueError("UNSUPPORTED_FILE: use .csv or .xlsx")
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > 2000 or sum(i.file_size for i in infos) > 200 * 1024 * 1024:
                raise ValueError("UNSAFE_WORKBOOK: decompression budget exceeded")
            if any(
                "vbaproject" in i.filename.lower() or "externallinks/" in i.filename.lower() for i in infos
            ):
                raise ValueError("UNSAFE_WORKBOOK: macros/external links forbidden")
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
        try:
            sheet = book["Products"] if "Products" in book.sheetnames else book.worksheets[0]
            # Ignore unreliable stored dimensions; bounded iteration below is authoritative.
            sheet.reset_dimensions()
            return _rows(sheet.iter_rows(values_only=True), mapping)
        finally:
            book.close()
    except (ValueError, UnicodeError, zipfile.BadZipFile, KeyError, OSError) as exc:
        raise ValueError(f"INVALID_FILE: {exc}") from exc
    except Exception as exc:
        raise ValueError("INVALID_FILE: malformed or unsupported workbook") from exc


def _rows(source, mapping):
    headers = normalize_headers(list(next(source, [])), mapping)
    if not headers or len(headers) > MAX_COLS or any(not h or h == "None" for h in headers):
        raise ValueError("INVALID_HEADERS")
    rows = []
    for rownum, values in enumerate(source, 2):
        if rownum > MAX_ROWS + 1:
            raise ValueError("TOO_MANY_ROWS: use batches of at most 100000")
        if len(values) > len(headers):
            raise ValueError(f"EXTRA_COLUMNS at row {rownum}")
        if any(isinstance(v, str) and len(v) > 16000 for v in values):
            raise ValueError("CELL_TOO_LONG")
        record = dict(zip(headers, list(values) + [None] * (len(headers) - len(values))))
        if len(json.dumps(record, default=str, ensure_ascii=False)) > 30000:
            raise ValueError("ROW_TOO_LARGE: audit cell must preserve all original values")
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
