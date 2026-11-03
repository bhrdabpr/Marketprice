"""Synthetic evidence only; independent arithmetic checks, no merchant records."""

import json
from decimal import ROUND_CEILING
from decimal import Decimal as D
from pathlib import Path
from time import perf_counter

from marketprice.flexible import calculate_catalog
from marketprice.importing import map_rows
from marketprice.io import read_upload

source = Path("samples/final-case-study.csv")
raw = read_upload(source.read_bytes(), source.name, preserve_headers=True)
mapping = {k: ("current_price" if k == "selling_toman" else k) for k in raw[0]}
rows = map_rows(raw, mapping, {"selling_toman": "TOMAN → IRR"})
started = perf_counter()
result = calculate_catalog(
    rows,
    currency="IRR",
    target_margin="10%",
    margins=(D(".15"), D(".25")),
    discounts=(D(".1"),),
    omitted_costs_confirmed=True,
)
elapsed = perf_counter() - started
assert [r["status"] for r in result["Product_Calculations"]] == ["VALID", "INVALID", "VALID"]
first = result["Product_Calculations"][0]
assert first["profit"] == D(1500000) * D(".8") - D(1010000)
expected = {}
for rate in (D(".1"), D(".15"), D(".25")):
    floor = (D(1010000) / (D(".8") - rate)).to_integral_value(rounding=ROUND_CEILING)
    record = next(
        r for r in result["Price_Recommendations"] if r["sku"] == "DEMO-001" and r["target_margin"] == rate
    )
    assert record["recommended_price"] == floor
    expected[str(rate)] = str(floor)
assert first["break_even"] == D(1262500)
print(
    json.dumps(
        {
            "products": 3,
            "valid": 2,
            "invalid": 1,
            "current_profit_irr": str(first["profit"]),
            "break_even_irr": "1262500",
            "margin_floors_irr": expected,
            "calculation_seconds": elapsed,
        },
        indent=2,
    )
)
