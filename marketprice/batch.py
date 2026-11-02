import hashlib
import json
from collections import Counter
from collections.abc import Callable
from decimal import Decimal

from .campaign import discount_limits, simulate
from .config import load_profiles
from .engine import VERSION, CalculationError, evaluate, floor_price
from .models import Product
from .recommendation import recommend
from .validation import issue, validate

D = Decimal
ZERO = D(0)
COST_FIELDS = frozenset(
    {
        "shipping",
        "fulfillment",
        "packaging",
        "warehouse",
        "overhead",
        "advertising",
        "other_fixed",
        "expected_return_cost",
        "marketplace_extra",
        "commission_rate",
        "commission_fixed",
        "payment_rate",
        "payment_fixed",
        "other_rate",
    }
)


def process(
    rows: list[dict],
    *,
    profiles=None,
    applicable_costs: set[str] | None = None,
    locale="en",
    margins: tuple[Decimal, ...] = (),
    discounts: tuple[Decimal, ...] = (D(".05"), D(".10"), D(".15"), D(".20")),
    platform_share=ZERO,
    campaign_kind="percent",
    override=False,
    progress: Callable | None = None,
) -> dict[str, list[dict]]:
    profiles = profiles if profiles is not None else load_profiles()
    if applicable_costs is not None and not applicable_costs <= COST_FIELDS:
        raise ValueError("Unknown applicable cost field")
    for margin in margins:
        if not margin.is_finite() or not 0 <= margin < 1:
            raise ValueError("INVALID_MARGIN_TARGET")
    if not platform_share.is_finite() or not 0 <= platform_share <= 1:
        raise ValueError("INVALID_PLATFORM_SHARE")
    if campaign_kind not in ("percent", "fixed") or any(
        not d.is_finite() or d < 0 or (campaign_kind == "percent" and d > 1) for d in discounts
    ):
        raise ValueError("INVALID_DISCOUNT")
    out: dict[str, list[dict]] = {
        name: []
        for name in (
            "Summary",
            "Product_Calculations",
            "Price_Recommendations",
            "Campaign_Simulations",
            "Errors",
            "Warnings",
            "Assumptions",
            "Marketplace_Rules",
            "Audit_Trail",
            "Data_Dictionary",
        )
    }
    counts = Counter(str(r.get("sku", "")).strip() for r in rows)
    valid = 0
    rule_hash = hashlib.sha256(
        json.dumps({k: v.model_dump(mode="json") for k, v in profiles.items()}, sort_keys=True).encode()
    ).hexdigest()
    for n, raw in enumerate(rows, 2):
        key: dict = {"row": n, "sku": str(raw.get("sku", ""))}
        prepared = dict(raw)
        if applicable_costs is not None:
            for field in COST_FIELDS - applicable_costs:
                # Only absent columns may be declared inapplicable. Present blanks remain errors.
                if field not in raw:
                    prepared[field] = "0"
        p, errors = validate(prepared, n, profiles, locale)
        if counts[key["sku"].strip()] > 1:
            errors.append(
                issue(key["sku"], n, "sku", "DUPLICATE_SKU", "Every duplicate occurrence is invalid")
            )
            p = None
        record = {**key, "status": "INVALID"}
        if p is not None:
            rule = profiles[p.marketplace]
            record.update(currency=p.currency, name=p.name, marketplace=p.marketplace)
            try:
                current = evaluate(p, rule, p.current_price)
                record.update(current.as_dict())
                record.update(break_even=floor_price(p, rule, D(0)))
                try:
                    record.update(discount_limits(p, rule))
                    if record["max_minimum_margin_discount"] is None:
                        out["Warnings"].append(
                            {
                                **key,
                                "code": "CAMPAIGN_TARGET_UNAVAILABLE",
                                "message": "No seller-funded discount meets campaign margin and permitted discount constraints.",
                            }
                        )
                except CalculationError as exc:
                    record.update(max_break_even_discount=None, max_minimum_margin_discount=None)
                    out["Warnings"].append(
                        {**key, "code": "CAMPAIGN_TARGET_UNAVAILABLE", "message": str(exc)}
                    )
                primary = recommend(p, rule, p.target_margin)
                recs = [{**key, "currency": p.currency, **primary}]
                # Optional scenarios can fail independently without invalidating the main recommendation.
                for margin in margins:
                    if margin == p.target_margin:
                        continue
                    try:
                        recs.append({**key, "currency": p.currency, **recommend(p, rule, margin)})
                    except CalculationError as exc:
                        out["Warnings"].append(
                            {**key, "code": "SCENARIO_UNAVAILABLE", "message": f"{margin}: {exc}"}
                        )
                record["status"] = "VALID"
                record["recommended_price"] = primary["recommended_price"]
                out["Price_Recommendations"].extend(recs)
                valid += 1
                for discount in discounts:
                    try:
                        out["Campaign_Simulations"].append(
                            {
                                **key,
                                "currency": p.currency,
                                **simulate(
                                    p,
                                    rule,
                                    discount,
                                    kind=campaign_kind,
                                    platform_share=platform_share,
                                    override=override,
                                ),
                            }
                        )
                    except CalculationError as exc:
                        out["Warnings"].append({**key, "code": "CAMPAIGN_UNAVAILABLE", "message": str(exc)})
                if current.margin is None or current.margin < p.target_margin:
                    out["Warnings"].append(
                        {
                            **key,
                            "code": "BELOW_TARGET",
                            "message": "Current margin is below target or undefined",
                        }
                    )
            except CalculationError as exc:
                errors.append(issue(p.sku, n, "pricing", str(exc).split(":")[0], str(exc)))
            out["Audit_Trail"].append(
                {
                    **key,
                    "engine_version": VERSION,
                    "profile": p.marketplace,
                    "rule_version": rule.version,
                    "rule_hash": rule_hash,
                    **{"input_" + k: v for k, v in p.model_dump(mode="json").items()},
                    "method": "piecewise-affine Decimal, upward grid rounding",
                    "status": record["status"],
                }
            )
        else:
            out["Audit_Trail"].append(
                {**key, "engine_version": VERSION, "rule_hash": rule_hash, "status": "INVALID"}
            )
        out["Errors"].extend(errors)
        record.update({"original_" + k: v for k, v in raw.items()})
        out["Product_Calculations"].append(record)
        if progress and (n % 100 == 0 or n == len(rows) + 1):
            progress((n - 1) / len(rows))
    out["Summary"] = [
        {"metric": "Products processed", "value": len(rows)},
        {"metric": "Valid products", "value": valid},
        {"metric": "Invalid products", "value": len(rows) - valid},
        {
            "metric": "Profit totals",
            "value": "No aggregate forecast: quantities are inventory, not sales predictions",
        },
    ]
    out["Assumptions"] = [
        {"setting": "Marketplace rules", "value": "Illustrative profiles, not verified official rates"},
        {
            "setting": "Margin denominator",
            "value": "Revenue excluding collected sales tax, including configured subsidy",
        },
        {
            "setting": "Precision",
            "value": "Decimal 50 digits; no per-fee settlement rounding; prices upward to increment",
        },
        {
            "setting": "Scenarios",
            "value": {
                "margins": [str(m) for m in margins],
                "discounts": [str(d) for d in discounts],
                "kind": campaign_kind,
                "platform_share": str(platform_share),
                "override": override,
                "locale": locale,
            },
        },
    ]
    out["Marketplace_Rules"] = [p.model_dump(mode="json") for p in profiles.values()]
    out["Data_Dictionary"] = [
        {
            "field": f,
            "required": v.is_required(),
            "type": str(v.annotation),
            "definition": FIELD_HELP.get(f, "Explicit per-order amount in row currency; no silent zero."),
        }
        for f, v in Product.model_fields.items()
    ]
    if applicable_costs is not None:
        out["Assumptions"].append(
            {
                "setting": "Workbook cost scope",
                "value": {
                    "applicable": sorted(applicable_costs),
                    "absent_inapplicable_columns": sorted(COST_FIELDS - applicable_costs),
                    "policy": "Present columns always validated; absent inapplicable costs explicitly treated as zero",
                },
            }
        )
    return out


FIELD_HELP = {
    "sku": "Unique text identifier; keep leading zeros.",
    "name": "Unicode product name.",
    "marketplace": "Versioned profile ID.",
    "category": "Category ID used for tier overrides.",
    "currency": "Explicit monetary unit; TOMAN is distinct from IRR.",
    "tax_mode": "inclusive or exclusive; applies to all selling price values.",
    "input_tax_credit": "Recoverable tax included in purchase_cost; subtracted once.",
    "fee_tax_recoverable": "true: fee tax credit offsets fee tax; false: seller expense.",
    "increment": "Positive multiple of currency minor unit; floors round upward.",
    "recommendation_rule": "floor, match_competitor, or keep_current.",
    "quantity": "Optional inventory count, never used as a sales forecast.",
    "expected_return_cost": "Explicit expected net return/refund loss per order; derive externally.",
    "target_margin": "Contribution/revenue fraction; 20% or 0.20, not 20.",
    "minimum_margin": "Mandatory regular/campaign minimum contribution margin.",
    "campaign_margin": "Campaign margin objective; mandatory minimum also applies.",
    "max_discount": "Maximum permitted customer discount fraction from current price.",
}
for _field in Product.model_fields:
    if _field.endswith("_rate"):
        FIELD_HELP[_field] = (
            "Explicit rate as fraction or percent text (0.10 or 10%); tax rules are user supplied."
        )
