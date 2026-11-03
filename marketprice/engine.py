"""Pure Decimal piecewise-affine contribution model; no network or UI dependencies."""

from dataclasses import asdict, dataclass
from decimal import ROUND_CEILING, Decimal, localcontext
from itertools import pairwise

from .models import FIXED_FIELDS, Product, Profile
from .precision import financial

D = Decimal
ZERO = D(0)
MAX_PRICE = D("1e18")
VERSION = "1.7.0"


class CalculationError(ValueError):
    pass


@dataclass(frozen=True)
class Ledger:
    price: Decimal
    customer_gross: Decimal
    subsidy: Decimal
    revenue: Decimal
    tax_collected: Decimal
    cogs: Decimal
    fixed_expenses: Decimal
    commission: Decimal
    payment: Decimal
    other_variable: Decimal
    fee_tax: Decimal
    fee_tax_credit: Decimal
    transaction_tax: Decimal
    total_cost: Decimal
    profit: Decimal
    margin: Decimal | None
    markup: Decimal | None

    def as_dict(self) -> dict:
        return asdict(self)


@financial
def round_up(value: Decimal, increment: Decimal) -> Decimal:
    return (value / increment).to_integral_value(rounding=ROUND_CEILING) * increment


def tiers_for(p: Product, rule: Profile):
    return rule.category_tiers.get(p.category, rule.tiers)


def commission(base: Decimal, p: Product, rule: Profile, campaign: bool) -> Decimal:
    tiers = tiers_for(p, rule)
    if not tiers:
        rate = (
            rule.campaign_commission_rate
            if campaign and rule.campaign_commission_rate is not None
            else p.commission_rate
        )
        return base * rate + p.commission_fixed
    result, lower = p.commission_fixed, D(0)
    for tier in tiers:
        upper = base if tier.up_to is None else min(base, tier.up_to)
        result += max(D(0), upper - lower) * tier.rate
        if tier.up_to is None or base <= tier.up_to:
            break
        lower = tier.up_to
    return result


@financial
def evaluate(
    p: Product,
    rule: Profile,
    price: Decimal,
    *,
    subsidy: Decimal = ZERO,
    list_price: Decimal | None = None,
    campaign: bool = False,
) -> Ledger:
    if not price.is_finite() or not subsidy.is_finite() or price < 0 or subsidy < 0:
        raise CalculationError("INVALID_PRICE")
    with localcontext() as ctx:
        ctx.prec = 50
        net = price / (1 + p.tax_rate) if p.tax_mode == "inclusive" else price
        gross = price if p.tax_mode == "inclusive" else price * (1 + p.tax_rate)
        # Subsidy is expressed in the same inclusive/exclusive units as price.
        sub_net = (
            subsidy / (1 + p.tax_rate) if rule.subsidy_taxable and p.tax_mode == "inclusive" else subsidy
        )
        sub_tax = (
            (subsidy - sub_net if p.tax_mode == "inclusive" else subsidy * p.tax_rate)
            if rule.subsidy_taxable
            else D(0)
        )
        revenue = net + sub_net
        tax = gross - net + sub_tax
        bases = {
            "net": net,
            "gross": gross,
            "list": price if list_price is None else list_price,
            "settlement": gross + sub_net + sub_tax,
        }
        comm = commission(bases[rule.commission_base], p, rule, campaign)
        payment = bases[rule.payment_base] * p.payment_rate + p.payment_fixed
        other = bases[rule.other_base] * p.other_rate
        fee_tax = (comm + payment) * p.fee_tax_rate
        credit = fee_tax if p.fee_tax_recoverable else D(0)
        cogs = p.purchase_cost - p.input_tax_credit
        fixed = sum((getattr(p, f) for f in FIXED_FIELDS), D(0))
        if campaign:
            fixed += rule.campaign_fixed_fee
        transaction_tax = revenue * p.transaction_tax_rate
        cost = cogs + fixed + comm + payment + other + fee_tax - credit + transaction_tax
        profit = revenue - cost
        return Ledger(
            price,
            gross,
            subsidy,
            revenue,
            tax,
            cogs,
            fixed,
            comm,
            payment,
            other,
            fee_tax,
            credit,
            transaction_tax,
            cost,
            profit,
            profit / revenue if revenue else None,
            profit / cost if cost else None,
        )


@financial
def floor_price(
    p: Product,
    rule: Profile,
    margin: Decimal,
    *,
    campaign: bool = False,
    list_price: Decimal | None = None,
    minimum_price: Decimal = ZERO,
    maximum_price: Decimal = MAX_PRICE,
) -> Decimal:
    """Find first feasible grid price across every progressive fee segment.

    In a segment profit - target*revenue is affine. Endpoints derive its slope;
    candidates are always re-evaluated. Handles decreasing/increasing tier rates.
    """
    if not margin.is_finite() or not D(0) <= margin < 1:
        raise CalculationError("INVALID_MARGIN_TARGET")
    with localcontext() as ctx:
        ctx.prec = 50
        k = 1 / (1 + p.tax_rate) if p.tax_mode == "inclusive" else D(1)
        base_k = {"net": k, "gross": k * (1 + p.tax_rate), "list": D(1), "settlement": k * (1 + p.tax_rate)}[
            rule.commission_base
        ]
        fixed_commission_base = rule.commission_base == "list" and list_price is not None
        bounds = [D(0)] + (
            []
            if fixed_commission_base
            else [t.up_to / base_k for t in tiers_for(p, rule) if t.up_to is not None]
        )
        bounds.append(D("1e18"))

        def residual(price):
            ledger = evaluate(p, rule, price, campaign=campaign, list_price=list_price)
            return ledger.profit - margin * ledger.revenue

        for left, right in pairwise(bounds):
            if left >= min(D("1e18"), maximum_price):
                continue
            right = min(right, D("1e18"), maximum_price)
            a = residual(left)
            slope = (residual(right) - a) / (right - left)
            candidate = max(p.increment, round_up(max(left, minimum_price), p.increment))
            if a < 0:
                if slope <= 0:
                    continue
                candidate = max(candidate, round_up(left - a / slope, p.increment))
            if candidate > right:
                continue
            # Decimal division may land just below a root; move at most one tick.
            if residual(candidate) < 0 and slope > 0:
                candidate += p.increment
            if candidate <= right and residual(candidate) >= 0:
                return candidate
    raise CalculationError("IMPOSSIBLE_MARGIN_TARGET: no feasible price within 1e18 model limit")
