"""Experimental local Excel companion using the same pricing engine.

The pure matrix boundary is tested; Excel/xlwings installation is optional.
"""

import json
from pathlib import Path
from uuid import uuid4

from .flexible import calculate_catalog
from .importing import map_rows
from .io import MAX_COLS, MAX_ROWS, json_default
from .templates import load_setup


def calculate_matrix(matrix, setup_bytes):
    if not matrix or len(matrix) < 2 or len(matrix) > MAX_ROWS + 1:
        raise ValueError("A header and 1–100000 product rows are required")
    headers = matrix[0]
    if (
        len(headers) > MAX_COLS
        or any(not isinstance(h, str) or not h for h in headers)
        or len(set(headers)) != len(headers)
    ):
        raise ValueError("Use distinct text headers in the first row")
    if any(len(row) != len(headers) for row in matrix):
        raise ValueError("Every row must match the header width")
    setup = load_setup(setup_bytes, headers)
    rows = map_rows([dict(zip(headers, row)) for row in matrix[1:]], setup["mapping"], setup["conversions"])
    settings = dict(setup["settings"])
    tax = settings.pop("seller_tax", None)
    if tax is not None and "transaction_tax_rate" not in rows[0]:
        rows = [{**r, "transaction_tax_rate": tax} for r in rows]
    if not {"currency", "target_margin"} <= settings.keys():
        raise ValueError("Save currency and target margin in the setup first")
    return calculate_catalog(rows, **settings)


def result_matrix(result):
    matrix = [
        [
            "MarketPrice — experimental Excel companion",
            "Source sheet unchanged; results are scenarios, not automatic price updates",
        ]
    ]
    for name in ("Action_List", "Price_Analysis", "Cost_Confidence", "Errors"):
        records = result[name]
        matrix.append([name])
        if not records:
            matrix.append(["No records"])
            continue
        headers = list(dict.fromkeys(k for r in records for k in r))
        matrix.append(headers)
        for row in records:
            matrix.append(
                [
                    json.dumps(row.get(k), default=json_default, ensure_ascii=False)
                    if isinstance(row.get(k), (dict, list))
                    else str(row.get(k, ""))
                    for k in headers
                ]
            )
    width = max(map(len, matrix))
    # Literal text only, including spreadsheet-formula-like merchant identifiers.
    return [
        [("'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value) for value in row]
        + [""] * (width - len(row))
        for row in matrix
    ]


def main():
    import xlwings as xw  # Optional: python -m pip install '.[excel]'

    book = xw.Book.caller()
    if not book.fullname or not Path(book.fullname).is_file():
        raise ValueError("Save the workbook before running MarketPrice")
    source = book.sheets.active
    if source.name.startswith("MP Results "):
        raise ValueError("Select your original product sheet before running again")
    used = source.used_range
    if used.rows.count > MAX_ROWS + 1 or used.columns.count > MAX_COLS:
        raise ValueError("Sheet exceeds the 100000-row / 80-column limit")
    setup_path = Path(book.fullname).with_suffix(".marketprice.json")
    if setup_path.stat().st_size > 65536:
        raise ValueError("Setup exceeds 64 KiB")
    result = calculate_matrix(used.options(ndim=2).value, setup_path.read_bytes())
    values = result_matrix(result)
    target = book.sheets.add("MP Results " + uuid4().hex[:8])
    block = target.range((1, 1), (len(values), len(values[0])))
    block.number_format = "@"
    block.value = values
    block.column_width = 24
    # Deliberately do not save, overwrite sources, or publish marketplace prices.
