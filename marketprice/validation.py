"""Normalize numbers without guessing percentage or decimal conventions."""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from .models import FIXED_FIELDS, Issue, Product, Profile

DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫٬٪", "01234567890123456789.,%")
ALIASES = {
    "کد کالا": "sku",
    "شناسه": "sku",
    "نام کالا": "name",
    "قیمت فروش": "current_price",
    "قیمت خرید": "purchase_cost",
    "هزینه ارسال": "shipping",
    "ارز": "currency",
    "بازار": "marketplace",
    "دسته بندی": "category",
    "کمیسیون": "commission_rate",
    "SKU": "sku",
    "Product name": "name",
    "Purchase cost": "purchase_cost",
    "Selling price": "current_price",
    "Shipping": "shipping",
}
TEXT = {"sku", "name", "marketplace", "category", "currency", "tax_mode", "recommendation_rule"}
OPTIONAL = {"quantity", "competitor_price", "price_ceiling", "price_minimum"}


def number(value: Any, locale: str = "en") -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean is not a number")  # noqa: TRY004 - validation contract
    if isinstance(value, (Decimal, int, float)):
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError("number must be finite")
        return result
    text = str(value).strip().translate(DIGITS)
    percent = text.endswith("%")
    if percent:
        text = text[:-1].strip()
    if locale == "comma":
        text = text.replace(".", "_").replace(",", ".").replace("_", ",")
    elif locale not in ("en", "fa"):
        raise ValueError("unsupported number locale")
    if not re.fullmatch(r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)", text):
        raise ValueError("invalid number or ambiguous grouping; select number locale")
    try:
        result = Decimal(text.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("invalid decimal") from exc
    return result / 100 if percent else result


def normalize_headers(headers: list, mapping: dict | None = None) -> list[str]:
    result = [(mapping or {}).get(str(h), ALIASES.get(str(h).strip(), str(h).strip())) for h in headers]
    if len(set(result)) != len(result):
        raise ValueError("DUPLICATE_COLUMNS: mapping must be one-to-one")
    return result


def issue(sku, row, field, code, explanation):
    return Issue(
        sku=str(sku),
        row=row,
        field=str(field),
        code=code,
        explanation=explanation,
        correction=f"Provide an explicit valid {field}; zero is allowed only when confirmed.",
    ).model_dump()


def validate(raw: dict, row: int, profiles: dict[str, Profile], locale: str = "en"):
    data: dict[str, Any] = {}
    errors: list[dict] = []
    sku = str(raw.get("sku", ""))
    for field, value in raw.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            if field in FIXED_FIELDS and not Product.model_fields[field].is_required():
                data[field] = None  # Present blanks must not activate an absent-column zero default.
            if field in OPTIONAL:
                continue
            # Leave required blanks absent: Pydantic reports missing, never zero.
            continue
        try:
            if field in TEXT:
                if field == "sku" and not isinstance(value, str):
                    raise ValueError("SKU must be stored as text to preserve identity and leading zeros")
                data[field] = str(value).strip()
            elif field == "fee_tax_recoverable":
                if str(value).lower() not in ("true", "false", "1", "0"):
                    raise ValueError("use true or false")
                data[field] = str(value).lower() in ("true", "1")
            else:
                if "%" in str(value).translate(DIGITS) and not (
                    field.endswith("_rate") or "margin" in field or field == "max_discount"
                ):
                    raise ValueError("percentage notation is invalid for monetary amounts")
                data[field] = number(value, locale)
        except ValueError as exc:
            errors.append(issue(sku, row, field, "INVALID_NUMBER", str(exc)))
    try:
        product = Product.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            field = str(err["loc"][0]) if err["loc"] else "row"
            code = "INVALID_INPUT"
            if err["type"] == "missing":
                code = {
                    "commission_rate": "MISSING_COMMISSION",
                    "shipping": "MISSING_SHIPPING_COST",
                    "purchase_cost": "MISSING_PURCHASE_COST",
                }.get(field, "MISSING_" + field.upper())
                if "tax" in field:
                    code = "MISSING_TAX_CONFIGURATION"
            elif "margin" in field:
                code = "INVALID_MARGIN_TARGET"
            elif "rate" in field or field == "max_discount":
                code = "INVALID_PERCENTAGE"
            elif "INVALID_CURRENCY" in err["msg"]:
                code = "INVALID_CURRENCY"
            errors.append(issue(sku, row, field, code, err["msg"]))
        return None, errors
    rule = profiles.get(product.marketplace)
    if rule is None:
        errors.append(issue(sku, row, "marketplace", "UNKNOWN_MARKETPLACE", "Select a configured profile"))
    else:
        for field in rule.required_fields:
            if getattr(product, field) is None:
                errors.append(
                    issue(sku, row, field, "MISSING_" + field.upper(), "Required by selected profile")
                )
    return (None if errors else product), errors

