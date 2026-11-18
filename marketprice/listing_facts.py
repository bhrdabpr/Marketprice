"""Seller-sourced facts and conservative checks; never a semantic certification."""

import re
import unicodedata
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation

FACT_COLUMNS = ("fact_id", "sku", "subject", "attribute", "value", "unit", "status", "source", "source_locator")
BOOLEAN_PATTERNS = {
    "insulated": r"\binsulated\b",
    "dishwasher_safe": r"\bdishwasher[ -]safe\b|\bsafe for (?:the )?dishwasher\b",
    "leakproof": r"\bleak[ -]?proof\b",
}
MEASURES = {"capacity": "volume", "height": "length", "width": "length", "length": "length", "weight": "mass"}
UNITS = {
    "ml": ("volume", "1"), "milliliter": ("volume", "1"), "میلی لیتر": ("volume", "1"),
    "l": ("volume", "1000"), "liter": ("volume", "1000"), "لیتر": ("volume", "1000"),
    "mm": ("length", "1"), "cm": ("length", "10"), "m": ("length", "1000"),
    "g": ("mass", "1"), "kg": ("mass", "1000"), "گرم": ("mass", "1"), "کیلوگرم": ("mass", "1000"),
}
TEXT_ATTRIBUTES = {"material", "compatibility", "product_type", "brand", "model", "color"}


def normalize(value):
    return " ".join(
        unicodedata.normalize("NFKC", str(value if value is not None else ""))
        .translate(str.maketrans("يك۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "یک01234567890123456789"))
        .replace("\u200c", " ").replace("٫", ".").casefold().split()
    )


@dataclass(frozen=True)
class ProductFact:
    fact_id: str
    sku: str
    subject: str
    attribute: str
    value: str
    unit: str
    status: str
    source: str
    source_locator: str

    def canonical_value(self):
        if self.attribute in MEASURES:
            return Decimal(normalize(self.value)) * Decimal(UNITS[normalize(self.unit)][1])
        if self.attribute == "pack_count":
            return Decimal(normalize(self.value))
        return normalize(self.value)


def parse_facts(rows):
    """Reject invalid evidence instead of silently dropping or guessing its meaning."""
    if len(rows) > 100_000:
        raise ValueError("FACT_LIMIT: use at most 100000 facts")
    result = []
    seen = set()
    for rownum, row in enumerate(rows, 2):
        if set(row) - set(FACT_COLUMNS):
            raise ValueError(f"FACT_COLUMNS at row {rownum}: use the provided facts template")
        values = {key: str(row.get(key) if row.get(key) is not None else "").strip() for key in FACT_COLUMNS}
        if not isinstance(row.get("sku"), str):
            raise ValueError(f"FACT_SKU at row {rownum}: SKU must be text to preserve its identity")  # noqa: TRY004 -- file validation contract
        for key in ("fact_id", "sku", "subject", "attribute", "value", "status"):
            if not values[key]:
                raise ValueError(f"FACT_REQUIRED at row {rownum}: {key}")
        if values["fact_id"] in seen:
            raise ValueError(f"FACT_DUPLICATE_ID at row {rownum}")
        seen.add(values["fact_id"])
        attribute = values["attribute"]
        if attribute not in set(MEASURES) | set(BOOLEAN_PATTERNS) | TEXT_ATTRIBUTES | {"pack_count"}:
            raise ValueError(f"FACT_ATTRIBUTE at row {rownum}: unsupported attribute")
        if values["status"] not in {"confirmed", "unverified", "disputed"}:
            raise ValueError(f"FACT_STATUS at row {rownum}: confirmed, unverified or disputed required")
        if values["status"] == "confirmed" and not values["source"]:
            raise ValueError(f"FACT_SOURCE at row {rownum}: confirmed facts need a source reference")
        if attribute in MEASURES or attribute == "pack_count":
            try:
                amount = Decimal(normalize(values["value"]))
            except InvalidOperation as exc:
                raise ValueError(f"FACT_NUMBER at row {rownum}: use an ungrouped decimal number") from exc
            if not amount.is_finite() or amount <= 0 or amount > Decimal("1e12"):
                raise ValueError(f"FACT_NUMBER at row {rownum}: positive finite value up to 1e12 required")
            exponent = amount.as_tuple().exponent
            if len(amount.as_tuple().digits) > 18 or not isinstance(exponent, int) or exponent < -12:
                raise ValueError(f"FACT_PRECISION at row {rownum}: at most 18 significant digits and 12 decimal places")
            if attribute == "pack_count":
                if amount != amount.to_integral_value() or values["unit"]:
                    raise ValueError(f"FACT_PACK_COUNT at row {rownum}: integer value with empty unit required")
            elif UNITS.get(normalize(values["unit"]), (None,))[0] != MEASURES[attribute]:
                raise ValueError(f"FACT_UNIT at row {rownum}: supported metric unit required")
        elif values["unit"]:
            raise ValueError(f"FACT_UNIT at row {rownum}: leave unit empty for this attribute")
        if attribute in BOOLEAN_PATTERNS and normalize(values["value"]) not in {"true", "false"}:
            raise ValueError(f"FACT_BOOLEAN at row {rownum}: true or false required")
        result.append(ProductFact(**values))
    return result


def evidence_rows(facts, confirmed, excluded_ids):
    return [{**asdict(f), "eligible": confirmed and f.status == "confirmed" and f.fact_id not in excluded_ids,
             "verification": "Seller-supplied; not independently verified"} for f in facts]


def conflict_groups(facts):
    grouped: dict[tuple, list] = {}
    for fact in facts:
        grouped.setdefault((normalize(fact.subject), fact.attribute), []).append(fact)
    return {key: group for key, group in grouped.items()
            if any(f.status == "disputed" for f in group)
            or len({f.canonical_value() for f in group if f.status == "confirmed"}) > 1}


def boolean_claims(text):
    """Recognize a small disclosed English vocabulary; retain ambiguous negation for review."""
    text = normalize(text)
    claims = []
    for attribute, pattern in BOOLEAN_PATTERNS.items():
        for match in re.finditer(pattern, text):
            prefix = re.split(r"[.;!?]", text[:match.start()])[-1]
            negative = bool(re.search(r"(?:\bnot|\bnon|\bnever)\s*[- ]?(?:\w+\s+){0,2}$", prefix))
            # Conditional wording does not establish an unconditional product property.
            suffix = re.split(r"[.;!]", text[match.end():], maxsplit=1)[0]
            uncertain = bool(re.search(r"\b(if|unless|may|might|whether|only)\b", prefix[-70:] + " " + suffix)) or "?" in suffix
            claims.append((attribute, None if uncertain else not negative, prefix))
    return claims


def check_claims(text, facts, legacy_reference=""):
    """Check only recognized assertions; unsupported constructions remain human-review work."""
    checked = []
    conflicts = conflict_groups(facts)
    normalized = normalize(text)
    legacy = boolean_claims(legacy_reference)
    for attribute, positive, prefix in boolean_claims(text):
        candidates = [f for f in facts if f.attribute == attribute
                      and (re.search(r"^\s*" + re.escape(normalize(f.subject))
                                     + r"\s+(?:is\s+)?(?:(?:not|non|never)\s*[- ]?)?$", prefix))]
        confirmed = [f for f in candidates if f.status == "confirmed"]
        expected = {f.canonical_value() for f in confirmed}
        ambiguous = positive is None or len({normalize(f.subject) for f in candidates}) > 1
        if any((normalize(f.subject), attribute) in conflicts for f in candidates):
            status, reason = "FACT_CONFLICT", "Supplied facts disagree or are disputed."
        elif ambiguous:
            status, reason = "CLAIM_REVIEW", "Claim scope or negation needs human review."
        elif expected:
            status = "SUPPORTED_FACT" if expected == {str(positive).lower()} else "CONTRADICTED_CLAIM"
            reason = "Compared with confirmed, source-linked facts for this SKU and subject."
        elif any(a == attribute and v is not None and v != positive for a, v, _ in legacy):
            status, reason = "NEGATION_REVIEW", "Reference text contains opposing wording; check subject and meaning."
        else:
            status, reason = "UNSUPPORTED_CLAIM", "No confirmed structured fact supports this recognized claim."
        checked.append({"attribute": attribute, "status": status, "observed": text,
                        "fact_ids": "; ".join(f.fact_id for f in candidates), "reason": reason})
    # Attribute/subject association is deliberately explicit, never pooled across entities.
    for (subject, attribute) in sorted({(normalize(f.subject), f.attribute) for f in facts if f.attribute in MEASURES}):
        group = [f for f in facts if normalize(f.subject) == subject and f.attribute == attribute]
        subject_pattern = re.escape(subject) + r"\s+"
        pattern = r"(?<!\w)" + subject_pattern + re.escape(attribute) + r"\s*(?:is\s+|of\s+|[:=]\s*)?(\d+(?:\.\d+)?)\s*([\w]+)\b"
        for match in re.finditer(pattern, normalized):
            unit = UNITS.get(match[2])
            prefix = re.split(r"[.;!?]", normalized[:match.start()])[-1]
            suffix = re.split(r"[.;!]", normalized[match.end():], maxsplit=1)[0]
            if prefix.strip() or "?" in suffix or re.search(r"\b(if|unless|may|might|only)\b", suffix):
                status = "MEASUREMENT_REVIEW"
            elif (subject, attribute) in conflicts:
                status = "FACT_CONFLICT"
            elif unit is None or unit[0] != MEASURES[attribute]:
                status = "MEASUREMENT_REVIEW"
            elif not any(f.status == "confirmed" for f in group):
                status = "UNSUPPORTED_CLAIM"
            else:
                observed = Decimal(match[1]) * Decimal(unit[1])
                expected = {f.canonical_value() for f in group if f.status == "confirmed"}
                status = "SUPPORTED_FACT" if observed in expected else "CONTRADICTED_CLAIM"
            checked.append({"attribute": f"{subject}.{attribute}", "status": status,
                            "observed": match[0], "fact_ids": "; ".join(f.fact_id for f in group),
                            "reason": "Explicit subject/attribute measurement compared with supplied facts."})
    return checked
