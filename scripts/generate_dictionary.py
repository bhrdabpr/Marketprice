import json
from pathlib import Path

from marketprice.batch import FIELD_HELP
from marketprice.models import Product, Profile

lines = [
    "# Input data dictionary",
    "",
    "One row is one independent SKU/order unit. Rates are fractions or explicit percent strings. All monetary inputs share the row currency. Unknown columns are rejected; map them explicitly.",
    "",
    "| Field | Required | Definition |",
    "|---|---|---|",
]
for name, field in Product.model_fields.items():
    definition = FIELD_HELP.get(name, "Explicit per-order amount in row currency; zero must be confirmed.")
    lines.append(
        f"| `{name}` | {'Yes' if field.is_required() else 'No; omitted means unused'} | {definition} |"
    )
Path("DATA_DICTIONARY.md").write_text("\n".join(lines) + "\n")
Path("docs/product.schema.json").write_text(json.dumps(Product.model_json_schema(), indent=2))
Path("docs/profile.schema.json").write_text(json.dumps(Profile.model_json_schema(), indent=2))
