"""Per-unit decisions and margin-constrained seasonal offers; no inventory forecasts."""

from decimal import Decimal

from .campaign import discount_limits, simulate
from .engine import evaluate
from .models import Product, Profile
from .precision import financial


@financial
def price_analysis(p: Product, rule: Profile, recommendation: dict) -> dict:
    price = recommendation["recommended_price"]
    # A computed floor is not evidence that a profitable price should be reduced.
    floor = recommendation["floor"]
    current = evaluate(p, rule, p.current_price)
    if (
        p.recommendation_rule == "floor"
        and p.current_price >= price
        and current.margin is not None
        and current.margin >= recommendation["target_margin"]
        and (p.price_ceiling is None or p.current_price <= p.price_ceiling)
    ):
        price = p.current_price
    difference = price - p.current_price
    ledger = evaluate(p, rule, price)
    action = "KEEP" if difference == 0 else ("INCREASE" if difference > 0 else "REVIEW_DECREASE")
    return {
        "currency": p.currency,
        "target_margin": recommendation["target_margin"],
        "current_price": p.current_price,
        "normal_price": price,
        "margin_floor": floor,
        "price_change": difference,
        "actual_margin": ledger.margin,
        "profit": ledger.profit,
        "action": action,
        "reason": "Cost floor only: retain a price meeting the objective; review any competitor-driven reduction. Costs and fee rules require confirmation; no demand prediction.",
    }


@financial
def seasonal_offers(
    p: Product, rule: Profile, event: tuple[str, Decimal, Decimal], platform_share: Decimal
) -> dict:
    name, margin, extra_cost = event
    candidate = p.model_copy(update={"campaign_margin": margin, "other_fixed": p.other_fixed + extra_cost})
    # Seller-funded ceiling is conservative when a platform subsidizes the discount.
    # Re-evaluate the final offer with the actual funding split.
    maximum = discount_limits(candidate, rule)["max_minimum_margin_discount"]
    base = {
        "event": name,
        "currency": p.currency,
        "current_price": p.current_price,
        "campaign_margin": margin,
        "campaign_cost": extra_cost,
        "objective": "Largest feasible seller-funded discount within configured margin/cap; actual funding verified. Not a demand optimum.",
    }
    if maximum is None or p.current_price <= 0:
        return {
            **base,
            "status": "NO_SAFE_OFFER",
            "suggested_discount": None,
            "campaign_price": None,
            "profit": None,
            "actual_margin": None,
        }
    offer = simulate(candidate, rule, maximum, platform_share=platform_share)
    if not offer["safe"]:
        return {
            **base,
            "status": "NO_SAFE_OFFER",
            "suggested_discount": None,
            "campaign_price": None,
            "profit": None,
            "actual_margin": None,
        }
    return {
        **base,
        "status": "SAFE",
        "suggested_discount": offer["actual_discount"] / p.current_price,
        "campaign_price": offer["campaign_price"],
        "profit": offer["profit"],
        "actual_margin": offer["margin"],
        "platform_share": platform_share,
        "baseline_unit_profit": evaluate(p, rule, p.current_price).profit,
        "required_sales_multiplier": (
            max(Decimal(0), evaluate(p, rule, p.current_price).profit) / offer["profit"]
            if offer["profit"] > 0
            else None
        ),
        "volume_note": "Units required to preserve baseline contribution; not predicted demand. Excludes campaign-wide fixed spend.",
    }
