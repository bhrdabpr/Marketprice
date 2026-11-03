"""Cost provenance and a compact, source-linked action queue."""

from .batch import COST_FIELDS
from .validation import number

COST_INPUTS = COST_FIELDS | {
    "purchase_cost",
    "transaction_tax_rate",
    "tax_rate",
    "input_tax_credit",
    "fee_tax_rate",
}
STATES = {"confirmed", "confirmed_zero", "estimated", "missing"}


def apply_confidence(result, rows, states=None, *, omitted_confirmed=False, locale="en"):
    if not isinstance(omitted_confirmed, bool) or (states is not None and not isinstance(states, dict)):
        raise ValueError("Invalid cost confirmation")
    states = states or {}
    if set(states) - COST_INPUTS or any(v not in STATES for v in states.values()):
        raise ValueError("Invalid cost confidence settings")
    columns = set().union(*(r.keys() for r in rows))
    summary = []
    actions = []
    by_row = {}
    for n, (raw, record) in enumerate(zip(rows, result["Product_Calculations"]), 2):
        missing, estimates, zeros = [], [], []
        for field in sorted(COST_INPUTS):
            state = states.get(
                field,
                "confirmed" if field in columns else ("confirmed_zero" if omitted_confirmed else "missing"),
            )
            value = raw.get(field, 0 if field not in columns and state == "confirmed_zero" else None)
            try:
                parsed = number(value, locale)
                if state == "confirmed_zero" and parsed != 0:
                    raise ValueError("Nonzero value declared zero")
            except ValueError:
                state = "missing"
            if state == "missing":
                missing.append(field)
            elif state == "estimated":
                estimates.append(field)
            elif state == "confirmed_zero" or parsed == 0:
                zeros.append(field)
        status = "MISSING" if missing else ("ESTIMATED" if estimates else "CONFIRMED_INPUTS")
        key = {"row": n, "sku": record["sku"], "currency": record.get("currency")}
        by_row[n] = status
        summary.append(
            {
                **key,
                "cost_confidence": status,
                "missing_costs": missing,
                "estimated_costs": estimates,
                "confirmed_zero_costs": zeros,
            }
        )
        record["cost_confidence"] = status
        if record["status"] != "VALID":
            actions.append(
                {
                    **key,
                    "priority": 1,
                    "action": "FIX_PRODUCT",
                    "impact": None,
                    "evidence": "Errors sheet, same source row",
                }
            )
        elif missing:
            actions.append(
                {
                    **key,
                    "priority": 1,
                    "action": "CONFIRM_COSTS",
                    "impact": None,
                    "evidence": ", ".join(missing),
                }
            )
        else:
            profit = record.get("profit")
            if profit is not None and profit < 0:
                actions.append(
                    {
                        **key,
                        "priority": 2,
                        "action": "REVIEW_LOSS",
                        "impact": -profit,
                        "evidence": "Expected loss per unit, not total sales loss",
                    }
                )
            elif estimates:
                actions.append(
                    {
                        **key,
                        "priority": 3,
                        "action": "VERIFY_ESTIMATES",
                        "impact": None,
                        "evidence": ", ".join(estimates),
                    }
                )
    seen = {a["row"] for a in actions}
    primary_rows = set()
    for record in result["Price_Analysis"]:
        if record["row"] in primary_rows:
            continue
        primary_rows.add(record["row"])
        if (
            by_row[record["row"]] == "CONFIRMED_INPUTS"
            and record["row"] not in seen
            and record["action"] == "INCREASE"
        ):
            actions.append(
                {
                    "row": record["row"],
                    "sku": record["sku"],
                    "currency": record["currency"],
                    "priority": 3,
                    "action": "REVIEW_MARGIN",
                    "impact": None,
                    "evidence": "Current price below configured objective; inspect primary Price_Analysis",
                }
            )
    for sheet in ("Price_Recommendations", "Price_Analysis", "Campaign_Simulations", "Seasonal_Campaigns"):
        for record in result[sheet]:
            status = by_row[record["row"]]
            record["cost_confidence"] = status
            record["decision_ready"] = status == "CONFIRMED_INPUTS"
            if status != "CONFIRMED_INPUTS":
                record["decision_note"] = (
                    "Provisional scenario; confirm missing/estimated costs and seller fee rules before acting."
                )
                if sheet == "Price_Analysis":
                    record["action"] = "CONFIRM_COSTS"
    result["Cost_Confidence"] = summary
    # Never rank monetary impacts across currencies.
    result["Action_List"] = sorted(
        actions, key=lambda r: (r["priority"], r["currency"] or "", -(r["impact"] or 0), r["row"])
    )
    result["Assumptions"].append(
        {
            "setting": "Cost confidence",
            "value": {
                "states": states,
                "omitted_costs_confirmed_zero": omitted_confirmed,
                "policy": "Absent unconfirmed costs use zero ONLY for provisional scenarios. Confirmed inputs are seller declarations, not independently verified contracts.",
            },
        }
    )
    return result
