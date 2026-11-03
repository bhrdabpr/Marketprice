"""Reconcile normalized signed transactions without inventing missing joins or costs.

Amounts are net of collected VAT in one explicit currency. Settlement transfers and
reserves affect cash reconciliation, never profit. Merchant data stays caller-owned.
"""

from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import date as Date
from decimal import Decimal
from typing import Literal

from pydantic import Field, ValidationError, model_validator

from .models import CURRENCIES, Money, StrictModel
from .precision import financial
from .validation import number

D = Decimal
KINDS = {
    "sale",
    "refund",
    "fee",
    "advertising",
    "tax",
    "cost",
    "cost_recovery",
    "adjustment",
    "reserve",
    "release",
    "payout",
}
CASH_KINDS = KINDS - {"cost", "cost_recovery", "payout"}
PROFIT_KINDS = KINDS - {"reserve", "release", "payout"}


class Transaction(StrictModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    marketplace: str = Field(min_length=1, max_length=128)
    currency: str
    date: Date
    kind: str
    amount: Decimal = Field(ge=D("-1e18"), le=D("1e18"), allow_inf_nan=False)
    order_id: str = ""
    sku: str = ""
    settlement_id: str = ""
    quantity: Decimal = Field(default=D(0), ge=0, le=D("1e9"), allow_inf_nan=False)
    expected_amount: Decimal | None = Field(default=None, ge=D("-1e18"), le=D("1e18"), allow_inf_nan=False)
    due_date: Date | None = None
    payment_type: Literal["cash", "credit", "unknown"] = "unknown"
    campaign: str = ""
    phase: Literal["before", "during", "after", ""] = ""

    @model_validator(mode="after")
    def check(self):
        if self.currency not in CURRENCIES or self.kind not in KINDS:
            raise ValueError("Unknown currency or transaction kind")
        unit = D(10) ** -CURRENCIES[self.currency]
        if self.amount % unit:
            raise ValueError("Amount exceeds currency precision")
        if self.kind in {"sale", "cost_recovery", "release", "payout"} and self.amount < 0:
            raise ValueError("This kind requires a nonnegative amount")
        if self.kind in {"refund", "fee", "advertising", "tax", "cost", "reserve"} and self.amount > 0:
            raise ValueError("Expenses/refunds/reserves must be negative")
        if self.kind == "sale" and (not self.sku or not self.order_id or self.quantity <= 0):
            raise ValueError("Sales require sku, order_id and positive quantity")
        if self.kind != "sale" and self.quantity != 0:
            raise ValueError("Quantity is recorded only on sales; returned costs use cost_recovery")
        if self.kind == "payout" and not self.settlement_id:
            raise ValueError("Payout requires settlement_id")
        if bool(self.campaign) != bool(self.phase):
            raise ValueError("Campaign and phase must be supplied together")
        return self


class Cost(StrictModel):
    sku: str = Field(min_length=1)
    currency: str
    effective_date: Date
    historical_unit_cost: Money
    replacement_unit_cost: Money
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def check(self):
        if self.currency not in CURRENCIES:
            raise ValueError("Unknown cost currency")
        return self


def parse_record(model, raw):
    clean = {k: v for k, v in raw.items() if v is not None and str(v).strip() != ""}
    for key in ("amount", "quantity", "expected_amount", "historical_unit_cost", "replacement_unit_cost"):
        if key in clean:
            if "%" in str(clean[key]) or "٪" in str(clean[key]):
                raise ValueError("Amounts cannot be percentages")
            clean[key] = number(clean[key])
    return model.model_validate(clean)


@financial
def reconcile(transactions: list[dict], costs: list[dict], *, as_of: Date) -> dict[str, list[dict]]:
    if not transactions or len(transactions) > 100000 or len(costs) > 100000:
        raise ValueError("Provide 1–100000 transactions and at most 100000 dated costs")
    errors, actions, parsed = [], [], []
    counts = Counter((str(r.get("marketplace")), str(r.get("transaction_id"))) for r in transactions)
    for row, raw in enumerate(transactions, 2):
        try:
            t = parse_record(Transaction, raw)
            if counts[(t.marketplace, t.transaction_id)] != 1:
                raise ValueError("Duplicate marketplace transaction ID: all occurrences excluded")
            if t.date > as_of:
                raise ValueError("Transaction is after the reporting date")
            parsed.append((row, t))
        except (ValueError, ValidationError) as exc:
            errors.append({"source": "Transactions", "row": row, "error": str(exc)[:1500]})
    histories = defaultdict(list)
    invalid_cost_keys = set()
    parsed_costs = []
    for row, raw in enumerate(costs, 2):
        try:
            parsed_costs.append((row, parse_record(Cost, raw)))
        except (ValueError, ValidationError) as exc:
            invalid_cost_keys.add((str(raw.get("sku")), str(raw.get("currency"))))
            errors.append({"source": "Costs", "row": row, "error": str(exc)[:1500]})
    cost_keys = Counter((c.sku, c.currency, c.effective_date) for _, c in parsed_costs)
    for row, c in parsed_costs:
        if cost_keys[(c.sku, c.currency, c.effective_date)] != 1:
            invalid_cost_keys.add((c.sku, c.currency))
            errors.append(
                {
                    "source": "Costs",
                    "row": row,
                    "error": "Duplicate dated cost; resolve before pricing this SKU",
                }
            )
        else:
            histories[(c.sku, c.currency)].append((row, c))
    for history in histories.values():
        history.sort(key=lambda pair: pair[1].effective_date)
    history_dates = {key: [c.effective_date for _, c in values] for key, values in histories.items()}
    orders = defaultdict(list)
    settlements = defaultdict(list)
    sources = []
    for row, t in parsed:
        key = (t.marketplace, t.currency, t.order_id)
        orders[key].append((row, t))
        if t.settlement_id:
            settlements[(t.marketplace, t.currency, t.settlement_id)].append((row, t))
        elif t.kind in CASH_KINDS:
            actions.append(
                {
                    "priority": 2,
                    "action": "UNMATCHED_SETTLEMENT",
                    "row": row,
                    "currency": t.currency,
                    "marketplace": t.marketplace,
                    "impact": abs(t.amount),
                    "evidence": t.transaction_id,
                }
            )
        sources.append({"source_row": row, **t.model_dump(mode="json")})
        if t.expected_amount is not None and t.amount != t.expected_amount:
            actions.append(
                {
                    "priority": 2,
                    "action": "EXPECTED_AMOUNT_DIFFERS",
                    "row": row,
                    "currency": t.currency,
                    "marketplace": t.marketplace,
                    "impact": abs(t.amount - t.expected_amount),
                    "evidence": f"{t.transaction_id}: expected {t.expected_amount}; actual {t.amount}",
                }
            )
    contributions = []
    campaign_groups = defaultdict(list)
    for (marketplace, currency, order_id), entries in orders.items():
        # Never attach unassigned account fees to arbitrary products.
        unallocated = not order_id
        sales = [(row, t) for row, t in entries if t.kind == "sale"]
        historical = D(0)
        replacement = D(0)
        missing = False
        cost_refs = []
        for row, t in sales:
            history = histories.get((t.sku, t.currency), [])
            dates_for_sku = history_dates.get((t.sku, t.currency), [])
            old_index = bisect_right(dates_for_sku, t.date) - 1
            new_index = bisect_right(dates_for_sku, as_of) - 1
            if old_index < 0 or new_index < 0 or (t.sku, t.currency) in invalid_cost_keys:
                missing = True
                actions.append(
                    {
                        "priority": 1,
                        "action": "MISSING_DATED_COST",
                        "row": row,
                        "currency": currency,
                        "marketplace": marketplace,
                        "impact": None,
                        "evidence": t.sku,
                    }
                )
                continue
            old, latest = history[old_index], history[new_index]
            historical += old[1].historical_unit_cost * t.quantity
            replacement += latest[1].replacement_unit_cost * t.quantity
            cost_refs.append(
                {"sale_row": row, "historical_cost_row": old[0], "replacement_cost_row": latest[0]}
            )
        profit_events = [t for _, t in entries if t.kind in PROFIT_KINDS]
        if not profit_events:
            continue
        # An orphan refund/fee may relate to a sale outside the reporting extract.
        orphan = bool(order_id) and not sales
        net = sum((t.amount for t in profit_events), D(0))
        revenue = sum((t.amount for t in profit_events if t.kind in {"sale", "refund"}), D(0))
        sales_skus = {t.sku for _, t in sales}
        sku_conflict = bool(sales and any(t.sku and t.sku not in sales_skus for t in profit_events))
        if sku_conflict:
            actions.append(
                {
                    "priority": 1,
                    "action": "ORDER_SKU_MISMATCH",
                    "marketplace": marketplace,
                    "currency": currency,
                    "impact": None,
                    "evidence": [n for n, _ in entries],
                }
            )
        complete = not (missing or orphan or errors or sku_conflict)
        contribution = net - historical if complete else None
        rec = {
            "marketplace": marketplace,
            "currency": currency,
            "order_id": order_id,
            "skus": sorted({t.sku for _, t in entries if t.sku}),
            "status": "UNALLOCATED" if unallocated else ("COMPLETE_INPUTS" if complete else "INCOMPLETE"),
            "net_revenue": revenue,
            "sales_revenue": sum((t.amount for t in profit_events if t.kind == "sale"), D(0)),
            "refunds": -sum((t.amount for t in profit_events if t.kind == "refund"), D(0)),
            "marketplace_advertising": -sum(
                (t.amount for t in profit_events if t.kind == "advertising"), D(0)
            ),
            "net_profit_events": net,
            "historical_cost": None if missing else historical,
            "replacement_cost": None if missing else replacement,
            "contribution": contribution,
            "replacement_contribution": net - replacement if complete else None,
            "units_sold": sum((t.quantity for _, t in sales), D(0)),
            "source_rows": [n for n, _ in entries],
            "cost_sources": cost_refs,
        }
        contributions.append(rec)
        if orphan or unallocated:
            actions.append(
                {
                    "priority": 2,
                    "action": "REVIEW_UNALLOCATED" if unallocated else "ORDER_SALE_MISSING",
                    "marketplace": marketplace,
                    "currency": currency,
                    "impact": abs(net),
                    "evidence": rec["source_rows"],
                }
            )
        if contribution is not None and contribution < 0:
            actions.append(
                {
                    "priority": 2,
                    "action": "REALIZED_LOSS",
                    "marketplace": marketplace,
                    "currency": currency,
                    "impact": -contribution,
                    "evidence": rec["source_rows"],
                }
            )
        tags = {(t.campaign, t.phase) for _, t in entries if t.campaign}
        if tags and (len(tags) != 1 or any(not t.campaign for t in profit_events)):
            actions.append(
                {
                    "priority": 2,
                    "action": "AMBIGUOUS_CAMPAIGN_ALLOCATION",
                    "marketplace": marketplace,
                    "currency": currency,
                    "impact": None,
                    "evidence": rec["source_rows"],
                }
            )
        elif tags:
            campaign, phase = next(iter(tags))
            campaign_groups[(marketplace, currency, campaign, phase)].append(rec)
    payout_report = []
    for (marketplace, currency, settlement_id), entries in settlements.items():
        expected = sum((t.amount for _, t in entries if t.kind in CASH_KINDS), D(0))
        paid = sum((t.amount for _, t in entries if t.kind == "payout"), D(0))
        has_activity = any(t.kind in CASH_KINDS for _, t in entries)
        has_payout = any(t.kind == "payout" for _, t in entries)
        dates = [t.due_date for _, t in entries if t.due_date]
        difference = paid - expected
        status = "MATCHED" if has_activity and has_payout and difference == 0 and not errors else "REVIEW"
        rec = {
            "marketplace": marketplace,
            "currency": currency,
            "settlement_id": settlement_id,
            "expected_payout": expected,
            "paid": paid,
            "difference": difference,
            "status": status,
            "overdue": bool(dates and max(dates) < as_of and paid < expected),
            "days_first_sale_to_last_payout": (
                (
                    max(t.date for _, t in entries if t.kind == "payout")
                    - min(t.date for _, t in entries if t.kind == "sale")
                ).days
                if any(t.kind == "sale" for _, t in entries) and has_payout
                else None
            ),
            "payment_types": sorted({t.payment_type for _, t in entries if t.kind == "sale"}),
            "source_rows": [n for n, _ in entries],
        }
        payout_report.append(rec)
        if status != "MATCHED":
            actions.append(
                {
                    "priority": 1 if rec["overdue"] else 2,
                    "action": "REVIEW_SETTLEMENT",
                    "marketplace": marketplace,
                    "currency": currency,
                    "impact": abs(difference),
                    "evidence": settlement_id,
                }
            )
    platform_groups = defaultdict(list)
    product_groups = defaultdict(list)
    for record in contributions:
        platform_groups[(record["marketplace"], record["currency"])].append(record)
        if len(record["skus"]) == 1 and record["order_id"]:
            product_groups[(record["marketplace"], record["currency"], record["skus"][0])].append(record)
    products = []
    for (marketplace, currency, sku), group in sorted(product_groups.items()):
        total = (
            sum((r["contribution"] for r in group), D(0))
            if all(r["contribution"] is not None for r in group)
            else None
        )
        units = sum((r["units_sold"] for r in group), D(0))
        products.append(
            {
                "marketplace": marketplace,
                "currency": currency,
                "sku": sku,
                "units_sold": units,
                "contribution_before_unallocated_costs": total,
                "contribution_per_sold_unit": total / units if total is not None and units else None,
                "refunds": sum((r["refunds"] for r in group), D(0)),
                "note": "Only single-SKU order groups; shared account costs and multi-SKU orders are not allocated.",
            }
        )
    platforms = []
    for platform_key, group in sorted(platform_groups.items()):
        complete = all(r["contribution"] is not None for r in group) and not errors
        units = sum((r["units_sold"] for r in group), D(0))
        total = sum((r["contribution"] for r in group), D(0)) if complete else None
        platforms.append(
            {
                "marketplace": platform_key[0],
                "currency": platform_key[1],
                "units_sold": units,
                "contribution": total,
                "contribution_per_sold_unit": total / units if total is not None and units else None,
                "status": "COMPLETE_INPUTS" if complete else "INCOMPLETE",
                "refunds": sum((r["refunds"] for r in group), D(0)),
                "marketplace_advertising": sum((r["marketplace_advertising"] for r in group), D(0)),
                "unallocated_net_events": sum(
                    (r["net_profit_events"] for r in group if r["status"] == "UNALLOCATED"), D(0)
                ),
            }
        )
    campaigns = []
    for (marketplace, currency, campaign, phase), group in sorted(campaign_groups.items()):
        complete = all(r["contribution"] is not None for r in group)
        campaigns.append(
            {
                "marketplace": marketplace,
                "currency": currency,
                "campaign": campaign,
                "phase": phase,
                "units_sold": sum((r["units_sold"] for r in group), D(0)),
                "contribution": sum((r["contribution"] for r in group), D(0)) if complete else None,
                "note": "Observed totals only; unequal periods, unallocated ads and attribution can distort comparisons. No causal uplift claim.",
            }
        )
    for error in errors:
        actions.append(
            {
                "priority": 1,
                "action": "FIX_SOURCE_ROW",
                "currency": "",
                "marketplace": "",
                "impact": None,
                "evidence": error,
            }
        )
    return {
        "Action_List": sorted(actions, key=lambda r: (r["priority"], r["currency"], -(r["impact"] or 0))),
        "Platform_Comparison": platforms,
        "Product_Platform": products,
        "Order_Contribution": contributions,
        "Settlement_Reconciliation": payout_report,
        "Campaign_Actuals": campaigns,
        "Source_Transactions": sources,
        "Source_Costs": [{"source_row": n, **r} for n, r in enumerate(costs, 2)],
        "Errors": errors,
        "Assumptions": [
            {
                "as_of": as_of.isoformat(),
                "policy": "Signed net-of-collected-VAT transactions; purchase COGS comes ONLY from cost history; cost events are additional external costs. Refunds do not automatically restore COGS. Cost recovery requires an explicit positive event. Cash reconciliation excludes external costs and COGS. No currency conversion. COMPLETE_INPUTS does not prove the extract contains all real transactions.",
            }
        ],
    }
