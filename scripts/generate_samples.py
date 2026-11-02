from pathlib import Path

from marketprice.batch import process
from marketprice.io import workbook_bytes
from marketprice.samples import sample_rows

p = Path("samples")
p.mkdir(exist_ok=True)
rows = sample_rows()
(p / "sample_input.xlsx").write_bytes(workbook_bytes({"Products": rows}))
(p / "sample_output.xlsx").write_bytes(workbook_bytes(process(rows)))
import csv

with (p / "sample_input.csv").open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

# Five/ten-cost examples use only the synthetic row factory above.
from marketprice.batch import COST_FIELDS
from marketprice.samples import sample_row

for count in (5, 10):
    fields = {"commission_rate", "shipping", "overhead", "payment_rate", "other_fixed"}
    if count == 10:
        fields |= {"fulfillment", "packaging", "warehouse", "advertising", "expected_return_cost"}
    base = {k: v for k, v in sample_row().items() if k not in COST_FIELDS or k in fields}
    examples = [
        {**base, "sku": "COMPLETE"},
        {**base, "sku": "MISSING-COMMISSION", "commission_rate": None},
        {**base, "sku": "ZERO-COMMISSION", "commission_rate": "0"},
    ]
    (p / f"{count}_costs.xlsx").write_bytes(workbook_bytes({"Products": examples}))
