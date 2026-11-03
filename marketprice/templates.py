"""Portable import setups contain mappings/settings, never merchant rows or secrets."""

import hashlib
import json

from .importing import IGNORE, UNMAPPED
from .models import Product

SETTINGS = {
    "currency",
    "target_margin",
    "marketplace",
    "locale",
    "seller_tax",
    "omitted_costs_confirmed",
    "cost_states",
}


def signature(headers):
    return hashlib.sha256(json.dumps(sorted(headers), ensure_ascii=False).encode()).hexdigest()


def save_setup(headers, mapping, conversions, settings):
    setup = {
        "version": 1,
        "header_signature": signature(headers),
        "mapping": mapping,
        "conversions": conversions,
        "settings": settings,
    }
    validate_setup(setup, headers)
    return json.dumps(setup, ensure_ascii=False, indent=2).encode()


def validate_setup(setup, headers):
    if not isinstance(setup, dict) or set(setup) != {
        "version",
        "header_signature",
        "mapping",
        "conversions",
        "settings",
    }:
        raise ValueError("Invalid saved setup")
    if setup["version"] != 1 or setup["header_signature"] != signature(headers):
        raise ValueError("Template changed: review columns and save a new setup")
    mapping, conversions, settings = setup["mapping"], setup["conversions"], setup["settings"]
    if not all(isinstance(x, dict) for x in (mapping, conversions, settings)):
        raise ValueError("Invalid setup sections")
    if set(mapping) != set(headers) or any(
        v not in [*Product.model_fields, IGNORE] for v in mapping.values()
    ):
        raise ValueError("Incomplete or unknown mapped fields")
    active = [v for v in mapping.values() if v not in (IGNORE, UNMAPPED)]
    if len(active) != len(set(active)) or "purchase_cost" not in active:
        raise ValueError("Duplicate fields or missing purchase cost")
    if set(conversions) - set(headers) or any(
        v not in ("As entered", "TOMAN → IRR", "Percentage number") for v in conversions.values()
    ):
        raise ValueError("Unknown conversions")
    if set(settings) - SETTINGS:
        raise ValueError("Unknown saved settings")
    if any(
        not isinstance(v, str)
        for k, v in settings.items()
        if k not in {"omitted_costs_confirmed", "cost_states"}
    ):
        raise ValueError("Invalid settings")
    if "omitted_costs_confirmed" in settings and not isinstance(settings["omitted_costs_confirmed"], bool):
        raise ValueError("Invalid cost confirmation")
    if "cost_states" in settings:
        from .confidence import COST_INPUTS, STATES

        states = settings["cost_states"]
        if (
            not isinstance(states, dict)
            or set(states) - COST_INPUTS
            or any(v not in STATES for v in states.values())
        ):
            raise ValueError("Invalid saved cost states")
        if any(
            v == "estimated" and k not in active and k != "transaction_tax_rate" for k, v in states.items()
        ):
            raise ValueError("Estimated fields must have mapped values")
    return setup


def load_setup(content, headers):
    if len(content) > 65536:
        raise ValueError("Setup exceeds 64 KiB")
    try:
        return validate_setup(json.loads(content), headers)
    except (TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid saved setup") from exc
