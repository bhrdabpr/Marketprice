"""Optional incremental capital-cost sensitivity; no payout prediction or fee defaults."""

from decimal import Decimal

from .precision import financial


@financial
def review_delay(result: dict[str, list[dict]], *, annual_rate: Decimal, extra_days: int) -> list[dict]:
    """Simple ACT/365 cost on net acquisition cost; preserve source financial results.

    Rate and delay are additional to financing already in the source calculation.
    This scenario excludes inventory holding time, tax-credit timing and other funded costs.
    """
    if (
        not isinstance(annual_rate, Decimal)
        or not annual_rate.is_finite()
        or not Decimal(0) <= annual_rate <= Decimal(10)
        or isinstance(extra_days, bool)
        or not isinstance(extra_days, int)
        or not 0 <= extra_days <= 3650
    ):
        raise ValueError("Enter an annual rate from 0–1000% and additional days from 0–3650")
    products = {r["row"]: r for r in result.get("Product_Calculations", [])}
    confidence = {r["row"]: r.get("cost_confidence") for r in result.get("Cost_Confidence", [])}
    reviewed = []
    scenarios = [("CURRENT", r) for r in products.values()]
    scenarios += [("CAMPAIGN", r) for r in result.get("Campaign_Simulations", [])]
    for kind, row in scenarios:
        product = products.get(row["row"], {})
        base = {
            "row": row["row"],
            "sku": row.get("sku"),
            "currency": product.get("currency"),
            "scenario": kind,
            "campaign_price": row.get("campaign_price"),
            "annual_rate": annual_rate,
            "extra_days": extra_days,
            "decision_ready": False,  # Sensitivity is never a marketplace approval.
        }
        if product.get("status") != "VALID" or product.get("cogs") is None or row.get("profit") is None:
            reviewed.append({**base, "delay_review": "FIX_PRODUCT"})
            continue
        capital = Decimal(str(product["cogs"]))
        before = Decimal(str(row["profit"]))
        cost = capital * annual_rate * extra_days / Decimal(365)
        after = before - cost
        confirmed = confidence.get(row["row"]) == "CONFIRMED_INPUTS"
        status = (
            "LOSS_AFTER_DELAY"
            if after < 0
            else ("BREAK_EVEN_AFTER_DELAY" if after == 0 else "POSITIVE_AFTER_DELAY")
        )
        reviewed.append(
            {
                **base,
                "capital_base": capital,
                "contribution_before_delay": before,
                "additional_capital_cost": cost,
                "contribution_after_delay": after,
                "source_cost_confidence": confidence.get(row["row"], "UNCONFIRMED"),
                "source_campaign_safe": row.get("safe") if kind == "CAMPAIGN" else None,
                "delay_review": status if confirmed else "CONFIRM_COSTS",
            }
        )
    return reviewed
