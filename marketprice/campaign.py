from decimal import ROUND_CEILING, Decimal

from .engine import CalculationError, evaluate, floor_price
from .models import CURRENCIES, Product, Profile
from .precision import financial

D = Decimal
ZERO = D(0)


@financial
def simulate(
    p: Product,
    rule: Profile,
    discount: Decimal,
    *,
    kind: str = "percent",
    platform_share: Decimal = ZERO,
    override: bool = False,
) -> dict:
    if (
        kind not in ("percent", "fixed")
        or not discount.is_finite()
        or discount < 0
        or not D(0) <= platform_share <= 1
    ):
        raise CalculationError("INVALID_DISCOUNT")
    if kind == "percent" and discount > 1:
        raise CalculationError("INVALID_PERCENTAGE")
    amount = p.current_price * discount if kind == "percent" else discount
    if amount > p.current_price:
        raise CalculationError("INVALID_DISCOUNT")
    unit = D(10) ** -CURRENCIES[p.currency]
    price = ((p.current_price - amount) / unit).to_integral_value(rounding=ROUND_CEILING) * unit
    actual_discount = p.current_price - price
    subsidy = actual_discount * platform_share
    ledger = evaluate(p, rule, price, subsidy=subsidy, list_price=p.current_price, campaign=True)
    threshold = max(p.minimum_margin, p.campaign_margin)
    feasible = ledger.profit >= 0 and ledger.margin is not None and ledger.margin >= threshold
    permitted = actual_discount <= p.current_price * p.max_discount
    safe = feasible and permitted
    return {
        "discount_kind": kind,
        "requested_discount": discount,
        "actual_discount": actual_discount,
        "platform_share": platform_share,
        "campaign_price": price,
        "subsidy": subsidy,
        "profit": ledger.profit,
        "margin": ledger.margin,
        "profit_change": ledger.profit - evaluate(p, rule, p.current_price).profit,
        "safe": safe,
        "approved": safe or override,
        "override": override,
        "warning": ""
        if safe
        else "UNSAFE_CAMPAIGN: loss, margin or discount limit violated; explicit override required",
    }


@financial
def discount_limits(p: Product, rule: Profile) -> dict:
    """Exact seller-funded grid limits including campaign/list fees and caps.

    Null means no feasible discount including zero within the selected domain.
    Individual intermediate discounts still require evaluation for nonmonotone tiers.
    """
    unit = D(10) ** -CURRENCIES[p.currency]
    campaign_product = p.model_copy(update={"increment": unit})

    def limit(margin, enforce_cap=False):
        if not p.current_price:
            return None
        try:
            price = floor_price(
                campaign_product,
                rule,
                margin,
                campaign=True,
                list_price=p.current_price,
                minimum_price=p.current_price * (1 - p.max_discount) if enforce_cap else ZERO,
                maximum_price=p.current_price,
            )
        except CalculationError:
            return None
        return (p.current_price - price) / p.current_price

    return {
        "max_break_even_discount": limit(D(0)),
        "max_minimum_margin_discount": limit(max(p.minimum_margin, p.campaign_margin), True),
        "discount_limit_note": "Seller-funded, exact campaign fee model; null means no feasible discount. Evaluate actual scenarios for nonmonotone tiers.",
    }
