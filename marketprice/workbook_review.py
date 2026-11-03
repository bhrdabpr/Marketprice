"""Inspect formula dependencies without calculating formulas or following external links."""

import io
import re

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from .confidence import COST_INPUTS


def price_dependent_costs(content: bytes, sheet_name: str, mapping: dict, data_rows: int) -> list[str]:
    price_columns = [
        get_column_letter(i) for i, field in enumerate(mapping.values(), 1) if field == "current_price"
    ]
    if not price_columns:
        return []
    pattern = re.compile(r"(?<![A-Z0-9_])\$?(?:" + "|".join(price_columns) + r")\$?\d+\b", re.IGNORECASE)
    book = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
    found = set()
    try:
        sheet = book[sheet_name]
        sheet.reset_dimensions()
        for row in sheet.iter_rows(min_row=2, max_row=data_rows + 1, values_only=True):
            for field, value in zip(mapping.values(), row):
                if (
                    field in COST_INPUTS
                    and isinstance(value, str)
                    and value.startswith("=")
                    and pattern.search(value)
                ):
                    found.add(field)
    finally:
        book.close()
    return sorted(found)
