"""Compare reported prices and sales within one market, category and currency."""

from collections import Counter
from decimal import Decimal
from statistics import median

from .models import CURRENCIES
from .precision import financial
from .validation import DIGITS, number

D = Decimal


@financial
def descriptive_fit(rows):
    """OLS association within a validated cohort, not causal elasticity."""
    if len(rows) < 3:
        return None
    x = [r["price"] for r in rows]
    y = [r["units"] / r["days"] for r in rows]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    variance = sum((v - mx) ** 2 for v in x)
    if not variance:
        return None
    slope = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / variance
    intercept = my - slope * mx
    total = sum((v - my) ** 2 for v in y)
    residual = sum((b - (slope * a + intercept)) ** 2 for a, b in zip(x, y, strict=True))
    return {"n": len(rows), "slope": slope, "intercept": intercept, "r_squared": max(D(0), D(1) - residual / total) if total else None}


def sales_rows(rows: list[dict], days: int) -> list[dict]:
    if not 1 <= days <= 366 or not 1 <= len(rows) <= 3000:
        raise ValueError("Use 1–3,000 rows and periods of 1–366 days.")
    output = []
    for row, raw in enumerate(rows, 2):
        try:
            sku, market, category, currency = (
                str(raw.get(k) or "").strip() for k in ("sku", "marketplace", "category", "currency")
            )
            if not all((sku, market, category)) or currency not in CURRENCIES:
                raise ValueError
            price, units, previous = (
                number(raw[k])
                for k in ("price", "units", "previous_units")
                if "%" not in str(raw[k]).translate(DIGITS)
            )
            if not 0 < price <= D("1e18") or any(
                not 0 <= n <= D("1e9") or n != int(n) for n in (units, previous)
            ):
                raise ValueError
            margins = [
                None if raw.get(k) is None or not str(raw[k]).strip() else number(raw[k])
                for k in ("margin", "target_margin")
            ]
            margin, target = margins
            if (margin is not None and margin > 1) or (target is not None and not 0 <= target < 1):
                raise ValueError
            output.append(
                {
                    "sku": sku,
                    "marketplace": market,
                    "category": category,
                    "currency": currency,
                    "price": price,
                    "units": units,
                    "previous_units": previous,
                    "margin": margin,
                    "target_margin": target,
                    "days": days,
                }
            )
        except (ValueError, KeyError, ArithmeticError) as exc:
            raise ValueError(f"Invalid sales row: {row}") from exc
    counts = Counter((r["marketplace"], r["category"], r["currency"], r["sku"]) for r in output)
    if max(counts.values()) > 1:
        raise ValueError("Duplicate SKU within comparison group.")
    return output


@financial
def compare(rows: list[dict]) -> tuple[list[dict], Decimal, Decimal]:
    """One group of validated rows with two equal periods. Ties stay neutral."""
    prices = median([r["price"] for r in rows])
    velocity = median([r["units"] / r["days"] for r in rows])

    def band(value, threshold, low, high):
        return low if value < threshold else high if value > threshold else "At benchmark"

    results = []
    for r in rows:
        rate = r["units"] / r["days"]
        previous = r["previous_units"]
        margin, target = r["margin"], r["target_margin"]
        risk = "Unknown"
        if margin is not None and margin < 0:
            risk = "Loss"
        elif margin is not None and target is not None:
            risk = "Below target" if margin < target else "At or above target"
        results.append(
            {
                **r,
                "units_per_day": rate,
                "price_band": band(r["price"], prices, "Lower price", "Higher price"),
                "sales_band": band(rate, velocity, "Slower sales", "Faster sales"),
                "growth_rate": (r["units"] - previous) / previous if previous else None,
                "trend": (
                    "New sales"
                    if not previous and r["units"]
                    else band(r["units"], previous, "Declining", "Growing").replace("At benchmark", "Stable")
                ),
                "margin_risk": risk,
            }
        )
    return results, prices, velocity
