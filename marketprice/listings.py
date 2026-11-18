"""Offline evidence-based listing checks. No keyword-volume or ranking predictions."""

import re
from collections import Counter
from decimal import Decimal

from .io import MAX_ROWS
from .listing_facts import UNITS, check_claims, conflict_groups, evidence_rows, normalize, parse_facts

VERSION = "1.2"
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

# Review explicit English claims about the range of jar, lid or bottle sizes.
FIT_CLAIM = re.compile(
    r"\b(?:works? (?:on|with)|opens?|fits?|adapts? to|handles?)\s+"
    r"(?:any|all|every)\s+(?:(?:tight|sizes?(?: of)?)\s+)?(?:jars?|lids?|bottles?)\b",
    re.IGNORECASE,
)
WORD_HYPHENS = str.maketrans(dict.fromkeys("-‐‑", " "))


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


def review_listings(rows, *, reference_confirmed=False, fact_rows=None, facts_confirmed=False):
    if not rows or len(rows) > MAX_ROWS:
        raise ValueError("Provide 1 to 100000 listing rows.")
    issues: list[dict] = []
    summaries: list[dict] = []
    keywords: list[dict] = []
    facts = parse_facts(fact_rows or [])
    identities = Counter(str(row.get("sku") or "").strip() for row in rows)
    if any(f.sku not in identities for f in facts):
        raise ValueError("FACT_SKU_MISMATCH: facts contain SKUs absent from the listing catalog")
    by_sku: dict[str, list] = {}
    for fact in facts:
        by_sku.setdefault(fact.sku, []).append(fact)
    unsafe_skus = {str(row.get("sku") or "").strip() for row in rows if not isinstance(row.get("sku"), str)}
    excluded_ids = {f.fact_id for sku, group in by_sku.items() for f in group
                    if identities[sku] != 1 or sku in unsafe_skus}
    for group in by_sku.values():
        for conflicting in conflict_groups(group).values():
            excluded_ids.update(f.fact_id for f in conflicting)
    claim_checks: list[dict] = []
    coverage: list[dict] = []
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

        if not sku or identities[sku] > 1:
            issue(
                "INVALID_IDENTITY",
                "sku",
                sku,
                "Missing or duplicate SKU within this file.",
                "Use a unique text SKU for each variant.",
                "ERROR",
            )
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
        supplied_facts = by_sku.get(sku, [])
        usable_facts = supplied_facts if facts_confirmed and identities[sku] == 1 and sku not in unsafe_skus else []
        if supplied_facts and not facts_confirmed:
            issue("FACTS_UNCONFIRMED", "facts", "", "Structured fact statuses have not been reviewed.",
                  "Review the sources and confirmation status for each fact.")
        for key, group in conflict_groups(usable_facts).items():
            issue("FACT_CONFLICT", "facts", "; ".join(f.fact_id for f in group),
                  f"Conflicting or disputed facts for {key[0]}.{key[1]}.",
                  "Resolve the evidence conflict before using this attribute.", "ERROR")
        bullet_columns = [f"bullet_{i}" for i in range(1, 11) if f"bullet_{i}" in row]
        fields_present = {f: row[f] for f in ("highlights", "description") if f in row}
        if bullet_columns:
            fields_present["bullet points"] = any(str(row[c] or "").strip() for c in bullet_columns)
        missing = [field for field, value in fields_present.items() if not str(value or "").strip()]
        if missing:
            issue("CONTENT_COMPLETENESS_REVIEW", "content", ", ".join(missing),
                  "These fields are blank in the supplied catalog row.",
                  "Check the source listing before deciding whether to add content.")
        unmapped = [f for f in ("highlights", "description", "bullet points") if f not in fields_present]
        coverage.append({"sku": sku, "row": rownum, "structured_facts": len(supplied_facts),
                         "content_fields_not_supplied": ", ".join(unmapped),
                         "fact_statuses_reviewed": facts_confirmed,
                         "claim_checks": "Limited English boolean claims and explicit subject/attribute metric measurements",
                         "not_checked": "Full semantics, material/compatibility claims, pack-count assertions, Arabic meaning, marketplace policy, search demand",
                         "overall": "HUMAN_REVIEW_REQUIRED"})
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
                if phrase_in(term, text.translate(WORD_HYPHENS)):
                    issue(
                        "VAGUE_WORDING",
                        field,
                        term,
                        "Generic praise does not describe a measurable product feature.",
                        "Replace with a specific, evidenced benefit or specification.",
                        "SUGGESTION",
                    )
            for check in check_claims(text, usable_facts, row.get("reference", "") if trusted else ""):
                claim_checks.append({"sku": sku, "row": rownum, "field": field, **check})
                if check["status"] != "SUPPORTED_FACT":
                    issue(check["status"], field, check["observed"], check["reason"],
                          "Verify this claim against the exact product's source-linked facts.",
                          "ERROR" if check["status"] in {"CONTRADICTED_CLAIM", "FACT_CONFLICT"} else "REVIEW")
            fit = FIT_CLAIM.search(text)
            if fit:
                issue("COMPATIBILITY_SCOPE_REVIEW", field, fit.group(),
                      "This wording describes broad jar, lid or bottle compatibility.",
                      "Check the stated limits against tested sizes and closure types.")
            number_text = norm
            if field.startswith("bullet_"):
                position = field.removeprefix("bullet_")
                number_text = re.sub(rf"^{position}[.)]\s+", "", norm)
            if re.search(r"\d", number_text):
                issue("MEASUREMENT_SCOPE_REVIEW", field, text,
                      "Numbers require attribute, subject and unit review; supported metric comparisons are only partial checks.",
                      "Check pack counts, ranges, unknown units and which component each value describes.")
            for dimension, values in quantities(text).items():
                if len(reference_quantities.get(dimension, set())) > 1:
                    issue("QUANTITY_CONTEXT_REQUIRED", field, text,
                          "Reference contains multiple values in this dimension; pooled values cannot validate components.",
                          "Provide separate subject/attribute facts for each component.")
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
            keyword_checks = check_claims(keyword, usable_facts, row.get("reference", "") if trusted else "")
            for check in keyword_checks:
                claim_checks.append({"sku": sku, "row": rownum, "field": "keywords", **check})
            failed_checks = [c for c in keyword_checks if c["status"] != "SUPPORTED_FACT"]
            if failed_checks:
                status, reason = failed_checks[0]["status"], failed_checks[0]["reason"]
            elif trusted and any(
                d in reference_quantities and not v <= reference_quantities[d]
                for d, v in quantities(keyword).items()
            ):
                status, reason = (
                    "QUANTITY_CONFLICT",
                    "Keyword quantity differs from confirmed reference facts.",
                )
            elif any(phrase_in(term, keyword.translate(WORD_HYPHENS)) for term in VAGUE):
                status, reason = (
                    "VAGUE",
                    "Generic promotional wording; no search-demand evidence is available.",
                )
            elif not trusted:
                status, reason = "NEEDS_EVIDENCE", "Confirm reference specifications first."
            elif candidate and candidate <= tokens(evidence):
                status, reason = (
                    "WORDS_PRESENT_REVIEW_REQUIRED",
                    "Word overlap is not factual support. Negation, intent and attribute meaning need review.",
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
            if status != "SUPPORTED_FACT":
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
                "status": "REVIEW_REQUIRED",
                "reference_confirmed": trusted,
                "decision_ready": False,
            }
        )
    return {
        "Listing_Summary": summaries,
        "Listing_Issues": issues,
        "Keyword_Review": keywords,
        "Original_Listings": rows,
        "Product_Facts": evidence_rows(facts, facts_confirmed, excluded_ids),
        "Claim_Checks": claim_checks,
        "Check_Coverage": coverage,
        "Method": [
            {
                "version": VERSION,
                "method": "Conservative wording, quantity and source-linked structured fact checks",
                "limitation": "No semantic verdict, marketplace certification, search volume or ranking forecast.",
            }
        ],
    }
