import argparse
import json
import platform
import time

from marketprice.batch import process
from marketprice.io import workbook_bytes
from marketprice.samples import sample_row

p = argparse.ArgumentParser()
p.add_argument("--rows", type=int, default=1000)
args = p.parse_args()
rows = [
    {
        **sample_row(f"SKU-{i:06}"),
        "purchase_cost": str(20 + i % 150),
        "shipping": str(i % 12),
        "commission_rate": str((i % 20) / 100),
        "current_price": str(150 + i % 200),
    }
    for i in range(args.rows)
]
t = time.perf_counter()
result = process(rows)
calculated = time.perf_counter()
blob = workbook_bytes(result)
end = time.perf_counter()
assert len(result["Product_Calculations"]) == args.rows and not result["Errors"]
print(
    json.dumps(
        {
            "rows": args.rows,
            "calculation_seconds": calculated - t,
            "export_seconds": end - calculated,
            "total_seconds": end - t,
            "xlsx_bytes": len(blob),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        indent=2,
    )
)
