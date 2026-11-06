"""Review observed offers against calculated campaigns; never predict Buy Box wins or demand."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlsplit

from .precision import financial
from .validation import number


@financial
def review_campaigns(
    result: dict[str, list[dict]], observations: list[dict], *, now: datetime | None = None
) -> list[dict]:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("Reporting time must include a timezone")
    indexed: dict[tuple[str, str], list[dict]] = {}
    for o in observations:
        indexed.setdefault((str(o.get("sku", "")), str(o.get("marketplace", ""))), []).append(o)
    products = {r["row"]: r for r in result.get("Product_Calculations", [])}
    reviewed = []
    for campaign in result.get("Campaign_Simulations", []):
        offer = {"marketplace": products.get(campaign.get("row"), {}).get("marketplace"), **campaign}
        base = {
            k: offer.get(k)
            for k in ("row", "sku", "marketplace", "currency", "campaign_price", "profit", "margin")
        }
        base.update(
            buy_box_prediction="NOT_PREDICTED", evidence_status="MISSING", review="ADD_COMPARABLE_OFFER"
        )
        if not offer.get("decision_ready") or not offer.get("safe"):
            reviewed.append({**base, "review": "CONFIRM_COSTS_OR_MARGIN"})
            continue
        candidates = indexed.get((str(offer.get("sku", "")), str(offer.get("marketplace", ""))), [])
        comparable = []
        rejected = 0
        rejection_reasons: list[str] = []
        for observation in candidates:
            try:
                if observation.get("match_confirmed") not in (True, "true") or observation.get(
                    "available"
                ) not in (True, "true"):
                    raise ValueError("Match/availability unconfirmed")
                if (
                    not isinstance(observation.get("product_reference"), str)
                    or not observation["product_reference"].strip()
                    or observation.get("currency") != offer.get("currency")
                ):
                    raise ValueError("Product reference/currency mismatch")
                url = urlsplit(str(observation.get("source_url", "")))
                if url.scheme != "https" or not url.netloc or url.username or url.password:
                    raise ValueError("Source URL required")
                observed = datetime.fromisoformat(str(observation["observed_at"]))
                if observed.tzinfo is None or not timedelta(0) <= now - observed <= timedelta(hours=24):
                    raise ValueError("Stale/future observation")
                if any(
                    "%" in str(observation.get(k, "")).replace("٪", "%")
                    for k in ("competitor_delivered_price", "our_customer_delivery_charge")
                ):
                    raise ValueError("Money is not a percentage")
                landed = number(observation["competitor_delivered_price"])
                own_delivery = number(observation["our_customer_delivery_charge"])
                if landed <= 0 or own_delivery < 0:
                    raise ValueError("Invalid delivered price")
                if (
                    not isinstance(observation.get("offer_condition"), str)
                    or not observation["offer_condition"].strip()
                    or observation["offer_condition"] != observation.get("our_condition")
                ):
                    raise ValueError("Condition differs")
                # Never substitute the seller shipping EXPENSE for the customer delivery charge.
                delta = number(offer["campaign_price"]) + own_delivery - landed
                comparable.append((landed, delta, observation))
            except (ValueError, KeyError, TypeError, OverflowError) as exc:
                rejected += 1
                rejection_reasons.append(str(exc)[:160])
        if not comparable:
            reviewed.append(
                {
                    **base,
                    "evidence_status": "REJECTED" if candidates else "MISSING",
                    "rejected_observations": rejected,
                    "rejection_reasons": rejection_reasons,
                }
            )
            continue
        price, gap, observation = min(comparable, key=lambda item: item[0])
        reviewed.append(
            {
                **base,
                "evidence_status": "REVIEWED_SELLER_INPUT",
                "review": "WITHIN_OBSERVED_PRICE" if gap <= Decimal(0) else "ABOVE_OBSERVED_PRICE",
                "competitor_delivered_price": price,
                "delivered_price_gap": gap,
                "source_url": observation["source_url"],
                "observed_at": observation["observed_at"],
                "rejected_observations": rejected,
                "rejection_reasons": rejection_reasons,
            }
        )
    return reviewed
