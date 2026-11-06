"""Offline quote-based sensitivity. Quotes are seller declarations, never verified market prices."""

import csv
from collections import Counter
from datetime import date
from decimal import ROUND_CEILING, Decimal
from io import StringIO

from pydantic import Field, field_validator, model_validator

from .approvals import snapshot
from .engine import CalculationError, floor_price
from .models import CURRENCIES, Money, Product, Profile, StrictModel
from .precision import financial
from .validation import number

D = Decimal
QUOTE_FIELDS = (
    "source_snapshot",
    "row",
    "sku",
    "marketplace",
    "currency",
    "replacement_net_unit_cost",
    "quoted_on",
    "valid_until",
    "source_reference",
)


class ReplacementQuote(StrictModel):
    source_snapshot: str = Field(pattern=r"^[0-9a-f]{64}$")
    row: int = Field(ge=2)
    sku: str = Field(min_length=1)
    marketplace: str = Field(min_length=1)
    currency: str
    replacement_net_unit_cost: Money
    quoted_on: date
    valid_until: date
    source_reference: str = Field(min_length=1, max_length=512)

    @field_validator("source_reference", "sku", "marketplace")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Empty quote identity/source")
        return value

    @model_validator(mode="after")
    def check(self):
        if self.currency not in CURRENCIES or self.valid_until < self.quoted_on:
            raise ValueError("Invalid quote currency or date range")
        return self


def quote_template(result: dict[str, list[dict]]) -> bytes:
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=QUOTE_FIELDS)
    writer.writeheader()
    stamp = snapshot(result)
    for row in result.get("Product_Calculations", []):
        if row.get("status") == "VALID":
            values = {key: row.get(key, "") for key in ("row", "sku", "marketplace", "currency")}
            # Quotes identify rows as well as SKUs. Avoid spreadsheet formula execution.
            for field in ("sku", "marketplace"):
                if str(values[field]).lstrip().startswith(("=", "+", "-", "@")):
                    values[field] = "'" + str(values[field])
            writer.writerow({**values, "source_snapshot": stamp})
    return stream.getvalue().encode("utf-8-sig")


@financial
def review_replacement(
    result: dict[str, list[dict]], quotes: list[dict], *, as_of: date
) -> dict[str, list[dict]]:
    if not isinstance(quotes, list) or len(quotes) > 100000 or any(not isinstance(q, dict) for q in quotes):
        raise ValueError("At most 100000 quote rows")
    stamp = snapshot(result)
    products = {r["row"]: r for r in result.get("Product_Calculations", [])}
    audits = {r["row"]: r for r in result.get("Audit_Trail", [])}
    confidence = {r["row"]: r.get("cost_confidence") for r in result.get("Cost_Confidence", [])}
    profiles = {r["id"]: Profile.model_validate(r) for r in result.get("Marketplace_Rules", [])}
    errors, parsed = [], []
    rejected_rows = set()
    for line, raw in enumerate(quotes, 2):
        try:
            if isinstance(raw.get("row"), bool):
                raise TypeError("Quote row must be an integer")
            amount = raw.get("replacement_net_unit_cost")
            if "%" in str(amount) or "٪" in str(amount):
                raise ValueError("Quote cost is an amount, not a percentage")
            quote = ReplacementQuote.model_validate({**raw, "replacement_net_unit_cost": number(amount)})
            product = products.get(quote.row)
            if not product:
                raise ValueError("Quote row does not exist in calculation")
            sku = str(product.get("sku"))
            allowed_sku = "'" + sku if sku.lstrip().startswith(("=", "+", "-", "@")) else sku
            market = str(product.get("marketplace"))
            allowed_market = "'" + market if market.lstrip().startswith(("=", "+", "-", "@")) else market
            if (
                quote.source_snapshot != stamp
                or quote.sku != allowed_sku
                or quote.currency != product.get("currency")
                or quote.marketplace != allowed_market
            ):
                raise ValueError("Quote calculation/identity/currency mismatch")
            if not quote.quoted_on <= as_of <= quote.valid_until:
                raise ValueError("Quote is future-dated or expired")
            parsed.append((line, quote))
        except (ValueError, TypeError) as exc:
            errors.append({"quote_row": line, "error": str(exc)[:1500]})
            try:
                rejected_rows.add(int(raw.get("row", "")))
            except (ValueError, TypeError, OverflowError):
                pass
    counts = Counter(q.row for _, q in parsed)
    accepted = {}
    for line, quote in parsed:
        if counts[quote.row] != 1 or quote.row in rejected_rows:
            rejected_rows.add(quote.row)
            errors.append({"quote_row": line, "error": "Duplicate/conflicting quotes for this source row"})
        else:
            accepted[quote.row] = quote
    reviewed = []
    campaigns: dict[int, list[dict]] = {}
    for campaign in result.get("Campaign_Simulations", []):
        campaigns.setdefault(campaign["row"], []).append(campaign)
    for row_id, product in products.items():
        base = {key: product.get(key) for key in ("row", "sku", "marketplace", "currency")}
        base.update(decision_ready=False, source_snapshot=stamp)
        if product.get("status") != "VALID":
            reviewed.append({**base, "replacement_review": "FIX_PRODUCT"})
            continue
        if row_id not in accepted:
            reviewed.append(
                {**base, "replacement_review": "FIX_QUOTE" if row_id in rejected_rows else "ADD_QUOTE"}
            )
            continue
        quote = accepted[row_id]
        raw_product = {
            k.removeprefix("input_"): v for k, v in audits[row_id].items() if k.startswith("input_")
        }
        # Internal zero enables floor-only calculations; no current profit is invented.
        raw_product.setdefault("current_price", "0")
        original = Product.model_validate(raw_product)
        replacement = Product.model_validate(
            {
                **original.model_dump(),
                "purchase_cost": quote.replacement_net_unit_cost,
                "input_tax_credit": D(0),
            }
        )
        delta = quote.replacement_net_unit_cost - (original.purchase_cost - original.input_tax_credit)
        rule = profiles[original.marketplace]
        floor = None
        constraint = "WITHIN_CONFIGURED_CONSTRAINTS"
        try:
            floor = floor_price(
                replacement, rule, replacement.target_margin, minimum_price=replacement.price_minimum or D(0)
            )
            if replacement.price_ceiling is not None and floor > replacement.price_ceiling:
                constraint = "PRICE_CONSTRAINT_CONFLICT"
        except CalculationError:
            constraint = "NO_FEASIBLE_REPLACEMENT_FLOOR"
        base.update(
            historical_net_unit_cost=original.purchase_cost - original.input_tax_credit,
            replacement_net_unit_cost=quote.replacement_net_unit_cost,
            replacement_cost_change=delta,
            replacement_margin_floor=floor,
            target_margin=original.target_margin,
            replacement_constraint=constraint,
            source_cost_confidence=confidence.get(row_id, "UNCONFIRMED"),
            quote_source=quote.source_reference,
            quoted_on=quote.quoted_on.isoformat(),
            valid_until=quote.valid_until.isoformat(),
        )
        scenarios = [("CURRENT", product), *[("CAMPAIGN", r) for r in campaigns.get(row_id, [])]]
        for kind, scenario in scenarios:
            before = scenario.get("profit")
            after = D(str(before)) - delta if before is not None else None
            status = (
                "FLOOR_ONLY"
                if after is None
                else ("LOSS_AT_REPLACEMENT" if after < 0 else "NONNEGATIVE_AT_REPLACEMENT")
            )
            if confidence.get(row_id) != "CONFIRMED_INPUTS":
                status = "CONFIRM_COSTS"
            reviewed.append(
                {
                    **base,
                    "scenario": kind,
                    "scenario_price": scenario.get("campaign_price", scenario.get("price")),
                    "historical_contribution": before,
                    "replacement_contribution": after,
                    "source_campaign_safe": scenario.get("safe") if kind == "CAMPAIGN" else None,
                    "replacement_review": status,
                }
            )
    return {
        "Replacement_Review": reviewed,
        "Quote_Errors": errors,
        "Assumptions": [
            {
                "as_of": as_of.isoformat(),
                "source_snapshot": stamp,
                "policy": "Seller-declared net acquisition quotes; no FX conversion, verified supplier price or demand forecast. Only acquisition cost changes; other costs/fees remain fixed to the source model. Financing and tax-credit timing are excluded. Scenario rows never approve a price change.",
            }
        ],
    }


@financial
def campaign_requirement(
    *, baseline_profit: Decimal, scenario_profit: Decimal, baseline_units: int, extra_spend: Decimal
) -> dict:
    """Single-SKU units needed to preserve historical contribution after incremental spend."""
    if (
        any(
            not isinstance(v, Decimal) or not v.is_finite() or abs(v) > D("1e18")
            for v in (baseline_profit, scenario_profit, extra_spend)
        )
        or extra_spend < 0
        or isinstance(baseline_units, bool)
        or not isinstance(baseline_units, int)
        or not 1 <= baseline_units <= 10**9
    ):
        raise ValueError("Invalid campaign budget assumptions")
    target = baseline_profit * baseline_units
    required = (
        int(((target + extra_spend) / scenario_profit).to_integral_value(rounding=ROUND_CEILING))
        if baseline_profit > 0 and scenario_profit > 0
        else None
    )
    return {
        "baseline_units": baseline_units,
        "baseline_total_contribution": target,
        "scenario_unit_contribution": scenario_profit,
        "additional_campaign_spend": extra_spend,
        "contribution_at_baseline_volume": scenario_profit * baseline_units - extra_spend,
        "required_units": required,
        "required_sales_multiplier": D(required) / baseline_units if required else None,
        "status": "REQUIREMENT_NOT_FORECAST" if required is not None else "NO_POSITIVE_COMPARISON",
        "decision_ready": False,
    }
