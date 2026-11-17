"""Offline evidence-based listing checks. No keyword-volume or ranking predictions."""

import re
import unicodedata
from decimal import Decimal

from .io import MAX_ROWS

VERSION = "1.0"
FIELDS = (
    "sku",
    "title",
    "highlights",
    "description",
    "keywords",
    "product_type",
    "brand",
    "model",
    "reference",
) + tuple(f"bullet_{i}" for i in range(1, 11))
ALIASES = {
    "item name": "title",
    "product name": "title",
    "name": "title",
    "عنوان": "title",
    "نام محصول": "title",
    "نام کالا": "title",
    "item highlights": "highlights",
    "نکات برجسته": "highlights",
    "توضیحات": "description",
    "search terms": "keywords",
    "search keywords": "keywords",
    "کلمات کلیدی": "keywords",
    "نوع محصول": "product_type",
    "برند": "brand",
    "مدل": "model",
    "verified facts": "reference",
    "مشخصات مرجع": "reference",
    "کد کالا": "sku",
    "bullet points": "bullet_1",
}
VAGUE = ("best", "amazing", "premium", "high quality", "must have", "بهترین", "عالی", "فوق العاده")
STOP = {"the", "a", "an", "for", "of", "and", "with", "in", "to", "و", "برای", "با", "از", "در"}
# Only comparable physical dimensions are checked; unit counts never use floating point.
UNITS = {
    "ml": ("volume", "1"),
    "milliliter": ("volume", "1"),
    "میلی لیتر": ("volume", "1"),
    "l": ("volume", "1000"),
    "liter": ("volume", "1000"),
    "لیتر": ("volume", "1000"),
    "mm": ("length", "1"),
    "cm": ("length", "10"),
    "m": ("length", "1000"),
    "g": ("mass", "1"),
    "kg": ("mass", "1000"),
    "گرم": ("mass", "1"),
    "کیلوگرم": ("mass", "1000"),
}


def normalize(value):
    return " ".join(
        unicodedata.normalize("NFKC", str(value or ""))
        .translate(str.maketrans("يك۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "یک01234567890123456789"))
        .replace("\u200c", " ")
        .replace("٫", ".")
        .casefold()
        .split()
    )


def tokens(value):
    return set(re.findall(r"[^\W_]+", normalize(value))) - STOP


def phrase_in(phrase, text):
    return bool(re.search(r"(?<!\w)" + re.escape(normalize(phrase)) + r"(?!\w)", normalize(text)))


def suggest_listing_mapping(headers):
    aliases = {normalize(f.replace("_", " ")): f for f in FIELDS}
    aliases.update(ALIASES)
    return {h: aliases.get(normalize(h).replace("_", " "), "Ignore") for h in headers}


def map_listing_rows(rows, mapping):
    targets = [v for v in mapping.values() if v != "Ignore"]
    if len(targets) != len(set(targets)):
        raise ValueError("Duplicate mapping: each listing field needs a unique column.")
    if not {"sku", "title"} <= set(targets):
        raise ValueError("Map SKU and title columns. Purchase costs are not required.")
    if set(targets) - set(FIELDS):
        raise ValueError("Unknown listing field.")
    return [
        {field: row.get(column) for column, field in mapping.items() if field != "Ignore"} for row in rows
    ]


def quantities(text):
    result: dict[str, set[Decimal]] = {}
    pattern = (
        r"(?<![\w.,٬])(\d+(?:\.\d+)?)\s*("
        + "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True))
        + r")(?!\w)"
    )
    for amount, unit in re.findall(pattern, normalize(text)):
        dimension, scale = UNITS[unit]
        result.setdefault(dimension, set()).add(Decimal(amount) * Decimal(scale))
    return result


def review_listings(rows, *, reference_confirmed=False):
    if not rows or len(rows) > MAX_ROWS:
        raise ValueError("Provide 1 to 100000 listing rows.")
    issues: list[dict] = []
    summaries: list[dict] = []
    keywords: list[dict] = []
    seen = set()
    for rownum, row in enumerate(rows, 2):
        sku = str(row.get("sku") or "").strip()
        start = len(issues)

        def issue(code, field, observed, reason, suggestion, severity="REVIEW", rownum=rownum, sku=sku):
            issues.append(
                {
                    "row": rownum,
                    "sku": sku,
                    "field": field,
                    "code": code,
                    "severity": severity,
                    "observed": str(observed or ""),
                    "reason": reason,
                    "suggestion": suggestion,
                }
            )

        if not sku or sku in seen:
            issue(
                "INVALID_IDENTITY",
                "sku",
                sku,
                "Missing or duplicate SKU within this file.",
                "Use a unique text SKU for each variant.",
                "ERROR",
            )
        seen.add(sku)
        if not isinstance(row.get("sku"), str):
            issue(
                "NUMERIC_IDENTITY",
                "sku",
                sku,
                "Numeric spreadsheet identifiers may have lost leading zeros.",
                "Confirm the original SKU; format source identifiers as text.",
            )
        title = str(row.get("title") or "").strip()
        if not title:
            issue(
                "MISSING_TITLE", "title", "", "No title supplied.", "Add an accurate product title.", "ERROR"
            )
        evidence = " ".join(str(row.get(f) or "") for f in ("product_type", "brand", "model", "reference"))
        trusted = bool(reference_confirmed and str(row.get("reference") or "").strip())
        if not trusted:
            issue(
                "EVIDENCE_REQUIRED",
                "reference",
                "",
                "Verified reference facts are missing or unconfirmed.",
                "Supply product specifications and confirm their source before judging factual accuracy.",
            )
        content_fields = (
            ("title", "highlights") + tuple(f"bullet_{i}" for i in range(1, 11)) + ("description",)
        )
        content_seen: dict[str, str] = {}
        reference_quantities = quantities(row.get("reference", "")) if trusted else {}
        for field in content_fields:
            text = str(row.get(field) or "").strip()
            if not text:
                continue
            norm = normalize(text)
            if norm in content_seen:
                issue(
                    "DUPLICATE_CONTENT",
                    field,
                    text,
                    f"Identical content also occurs in {content_seen[norm]}.",
                    "Use this space for a different supported product detail.",
                )
            content_seen[norm] = field
            if re.search(r"<\s*(script|iframe)\b|javascript:", text, re.IGNORECASE):
                issue(
                    "ACTIVE_CONTENT",
                    field,
                    text,
                    "Potential active HTML or script content.",
                    "Remove scripts and use plain listing text.",
                    "ERROR",
                )
            for term in VAGUE:
                if phrase_in(term, text):
                    issue(
                        "VAGUE_WORDING",
                        field,
                        term,
                        "Generic praise does not describe a measurable product feature.",
                        "Replace with a specific, evidenced benefit or specification.",
                        "SUGGESTION",
                    )
            for dimension, values in quantities(text).items():
                if dimension in reference_quantities and not values <= reference_quantities[dimension]:
                    issue(
                        "QUANTITY_CONFLICT",
                        field,
                        text,
                        f"{dimension} values differ from confirmed reference: {row.get('reference')}",
                        "Check whether this is a wrong variant, accessory dimension or incorrect claim.",
                    )
        if trusted:
            for field in ("brand", "model"):
                fact = str(row.get(field) or "").strip()
                # Generic is a brand-field classification, not a mandatory title keyword.
                if field == "brand" and normalize(fact) in {"generic", "unbranded", "no brand"}:
                    continue
                if fact and title and not phrase_in(fact, title):
                    issue(
                        "IDENTITY_NOT_IN_TITLE",
                        "title",
                        fact,
                        f"The supplied {field} is absent from the title.",
                        "Check product identity and compatibility wording before adding it.",
                    )
        for keyword in re.split(r"[;,\n،؛]+", str(row.get("keywords") or "")):
            keyword = keyword.strip()
            if not keyword:
                continue
            candidate = tokens(keyword)
            overlap = candidate & tokens(evidence)
            if trusted and any(
                d in reference_quantities and not v <= reference_quantities[d]
                for d, v in quantities(keyword).items()
            ):
                status, reason = (
                    "QUANTITY_CONFLICT",
                    "Keyword quantity differs from confirmed reference facts.",
                )
            elif any(phrase_in(term, keyword) for term in VAGUE):
                status, reason = (
                    "VAGUE",
                    "Generic promotional wording; no search-demand evidence is available.",
                )
            elif not trusted:
                status, reason = "NEEDS_EVIDENCE", "Confirm reference specifications first."
            elif candidate and candidate <= tokens(evidence):
                status, reason = (
                    "SUPPORTED_WORDS",
                    "Words occur in supplied product facts; intent still needs review.",
                )
            else:
                status = "REVIEW_RELEVANCE"
                reason = (
                    "Only some words match product facts." if overlap else "No words match product facts."
                )
                reason += " This may be irrelevant or a valid synonym; lexical matching cannot decide."
            keywords.append(
                {
                    "row": rownum,
                    "sku": sku,
                    "keyword": keyword,
                    "status": status,
                    "reason": reason,
                    "evidence": evidence,
                    "matched_words": ", ".join(sorted(overlap)),
                }
            )
            if status != "SUPPORTED_WORDS":
                issue(
                    "KEYWORD_" + status,
                    "keywords",
                    keyword,
                    reason,
                    "Verify relevance to the exact product and variant; remove only after review.",
                )
        summaries.append(
            {
                "row": rownum,
                "sku": sku,
                "title": title,
                "issues": len(issues) - start,
                "status": "REVIEW" if len(issues) > start else "NO_FLAGS_IN_CHECKED_RULES",
                "reference_confirmed": trusted,
                "decision_ready": False,
            }
        )
    return {
        "Listing_Summary": summaries,
        "Listing_Issues": issues,
        "Keyword_Review": keywords,
        "Original_Listings": rows,
        "Method": [
            {
                "version": VERSION,
                "method": "Offline lexical and explicit quantity checks",
                "limitation": "No semantic verdict, marketplace certification, search volume or ranking forecast.",
            }
        ],
    }
