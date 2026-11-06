"""Explicit file-wide defaults; present cells are never silently repaired."""

from dataclasses import fields
from decimal import Decimal

from .batch import COST_FIELDS, process
from .confidence import apply_confidence
from .engine import Ledger
from .io import MAX_ROWS
from .models import CURRENCIES, Product
from .validation import number

TAX_FIELDS = {"transaction_tax_rate", "tax_rate", "input_tax_credit", "fee_tax_rate"}


def calculate_catalog(
    rows: list[dict],
    *,
    currency: str,
    target_margin: str,
    marketplace: str = "generic",
    locale: str = "en",
    cost_states: dict[str, str] | None = None,
    omitted_costs_confirmed: bool = False,
    **options,
) -> dict[str, list[dict]]:
    """Absent costs are provisional zero until confirmed; included columns require every row.

    Currency and objective are explicit file-level settings. Row values override them.
    No current price means a floor only, with no invented campaign or current profit.
    """
    if not rows or len(rows) > MAX_ROWS or any(not isinstance(r, dict) for r in rows):
        raise ValueError("Provide 1 to 100000 product objects")
    if currency not in CURRENCIES:
        raise ValueError("INVALID_CURRENCY")
    margin = number(target_margin, locale)
    if not 0 <= margin < 1:
        raise ValueError("INVALID_MARGIN_TARGET")
    columns = set().union(*(r.keys() for r in rows))
    if not columns <= Product.model_fields.keys():
        raise ValueError(
            "Map or explicitly ignore unrecognized columns: "
            + ", ".join(sorted(columns - Product.model_fields.keys()))
        )
    defaults = {
        **{f: "0" for f in COST_FIELDS | TAX_FIELDS},
        "currency": currency,
        "marketplace": marketplace,
        "category": "general",
        "current_price": "0",  # Internal placeholder removed from all user-facing current results.
        "tax_mode": "exclusive",
        "fee_tax_recoverable": "false",
        "target_margin": margin,
        "minimum_margin": "0",
        "campaign_margin": margin,
        "max_discount": "1",
        "increment": Decimal(10) ** -CURRENCIES[currency],
        "recommendation_rule": "floor",
    }
    prepared = []
    for index, row in enumerate(rows, 2):
        item: dict = {f: None for f in columns}
        item.update({k: v for k, v in defaults.items() if k not in columns})
        item.update(row)
        if "sku" not in columns:
            item["sku"] = f"ROW-{index}"
        if "name" not in columns:
            item["name"] = str(item.get("sku", f"ROW-{index}"))
        # Currency-specific grid when mixed currencies are explicitly supplied.
        if (
            "increment" not in columns
            and isinstance(item.get("currency"), str)
            and item["currency"] in CURRENCIES
        ):
            item["increment"] = Decimal(10) ** -CURRENCIES[item["currency"]]
        if "current_price" not in columns and item.get("recommendation_rule") != "floor":
            item["current_price"] = None
        prepared.append(item)
    result = process(prepared, locale=locale, **options)
    for raw, record in zip(rows, result["Product_Calculations"]):
        for key in list(record):
            if key.startswith("original_"):
                record.pop(key)
        record.update({"original_" + k: v for k, v in raw.items()})
    if "current_price" not in columns:
        result["Campaign_Simulations"] = []
        result["Seasonal_Campaigns"] = []
        for decision in result["Price_Analysis"]:
            decision.update(current_price=None, price_change=None, action="SET_PRICE")
        for record in result["Product_Calculations"]:
            for field in fields(Ledger):
                record.pop(field.name, None)
            for key in (
                "max_break_even_discount",
                "max_minimum_margin_discount",
                "discount_limit_note",
                "original_current_price",
            ):
                record.pop(key, None)
            record["current_price_status"] = "NOT_PROVIDED"
        for audit in result["Audit_Trail"]:
            audit.pop("input_current_price", None)
            audit["current_price_status"] = "NOT_PROVIDED"
        result["Warnings"] = [
            r for r in result["Warnings"] if r["code"] not in {"BELOW_TARGET", "CAMPAIGN_TARGET_UNAVAILABLE"}
        ]
        result["Warnings"].append(
            {
                "code": "CURRENT_PRICE_NOT_PROVIDED",
                "message": "Price floors calculated; add current_price to assess campaigns and current profit.",
            }
        )
    result["Assumptions"].append(
        {
            "setting": "Flexible catalog settings",
            "value": {
                "absent_column_defaults": {k: v for k, v in defaults.items() if k not in columns},
                "generated_identity": "sku" not in columns,
                "policy": "Absent costs are provisional unless confirmed in Cost_Confidence. Present blank or missing cells invalidate only that product. Rates are fractions or percent text. No exchange-rate conversion.",
            },
        }
    )
    return apply_confidence(result, rows, cost_states, omitted_confirmed=omitted_costs_confirmed, locale=locale)

