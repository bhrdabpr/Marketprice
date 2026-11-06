"""Review-only change manifests; no automatic marketplace publication."""

import hashlib
import json

from .io import json_default


def snapshot(result):
    return hashlib.sha256(json.dumps(result, default=json_default, sort_keys=True).encode()).hexdigest()


def approved_changes(result, selections, *, expected_snapshot, fee_rules_confirmed=False):
    if not fee_rules_confirmed:
        raise ValueError("Review seller-specific fee rules before approving price changes")
    if snapshot(result) != expected_snapshot:
        raise ValueError("Results changed; approvals are stale")
    selected = set(selections)
    if len(selected) != len(selections):
        raise ValueError("Duplicate approvals")
    candidates = {(r["row"], str(r["target_margin"])): r for r in result["Price_Analysis"]}
    if selected - candidates.keys():
        raise ValueError("Unknown approval")
    updates, rows = [], set()
    for key in selections:
        r = candidates[key]
        if r["row"] in rows:
            raise ValueError("Choose only one margin scenario per source row")
        rows.add(r["row"])
        if r.get("cost_confidence") != "CONFIRMED_INPUTS" or not r.get("decision_ready") or r["action"] not in {
            "INCREASE",
            "REVIEW_DECREASE",
            "KEEP",
            "SET_PRICE",
        }:
            raise ValueError("Confirm costs before approving")
        if r["normal_price"] < r["margin_floor"]:
            raise ValueError("Price is below its margin floor")
        updates.append(
            {
                "row": r["row"],
                "sku": r["sku"],
                "currency": r["currency"],
                "previous_price": r["current_price"],
                "approved_price": r["normal_price"],
                "margin_floor": r["margin_floor"],
                "target_margin": r["target_margin"],
                "action": r["action"],
                "source_snapshot": expected_snapshot,
                "publication_status": "NOT_PUBLISHED",
            }
        )
    return updates

