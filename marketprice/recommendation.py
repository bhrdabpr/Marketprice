from decimal import Decimal

from .engine import CalculationError, evaluate, floor_price, round_up
from .models import Product, Profile
from .precision import financial


@financial
def recommend(p: Product, rule: Profile, margin: Decimal) -> dict:
    margin = max(margin, p.minimum_margin)
    floor = floor_price(p, rule, margin)
    desired = floor
    if p.recommendation_rule == "match_competitor":
        desired = max(floor, p.competitor_price or floor)
    elif p.recommendation_rule == "keep_current":
        desired = max(floor, p.current_price)
    desired = round_up(max(desired, p.price_minimum or floor), p.increment)
    if p.price_ceiling is not None and desired > p.price_ceiling:
        raise CalculationError("PRICE_CONSTRAINT_CONFLICT: recommendation exceeds price ceiling")
    ledger = evaluate(p, rule, desired)
    if ledger.margin is None or ledger.margin < margin:
        raise CalculationError("PRICE_CONSTRAINT_CONFLICT: higher price fails target under configured tiers")
    return {
        "target_margin": margin,
        "floor": floor,
        "recommended_price": desired,
        "actual_margin": ledger.margin,
        "profit": ledger.profit,
        "customer_gross": ledger.customer_gross,
        "explanation": f"{p.recommendation_rule}; floor {floor}; rounded upward to {p.increment}; no demand optimization",
    }
