"""Reviewable header suggestions; marketplace columns are never mixed."""

import re
import unicodedata

from .models import Product
from .validation import ALIASES as LEGACY_ALIASES
from .validation import number

IGNORE = "Ignore column"
UNMAPPED = "Choose field…"


def header_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).translate(str.maketrans("يك", "یک"))
    return re.sub(r"[\s\u200c_\-]+", " ", value).strip().casefold()


ALIASES = {
    **LEGACY_ALIASES,
    "کد": "sku",
    "کد کالا": "sku",
    "commission": "commission_rate",
    "commission rate": "commission_rate",
    "comision": "commission_rate",
    "هزیته ارسال": "shipping",
    "shipping cost": "shipping",
    "purchase price": "purchase_cost",
    "نام": "name",
    "نام محصول": "name",
    "نام کالا": "name",
    "تعداد": "quantity",
    "موجودی": "quantity",
    "هزینه ثابت": "overhead",
    "قیمت خرید": "purchase_cost",
    "قیمت فروش": "current_price",
    "هزینه ارسال": "shipping",
    "کمیسیون": "commission_rate",
    "دسته بندی": "category",
    "ارز": "currency",
    "buy price": "purchase_cost",
    "buying price": "purchase_cost",
    "cost price": "purchase_cost",
    "product name": "name",
    "product id": "sku",
    "selling price": "current_price",
    "tax amount": "other_fixed",
    "مبلغ مالیات": "other_fixed",
    "seller tax rate": "transaction_tax_rate",
    "نرخ مالیات فروشنده": "transaction_tax_rate",
    "بارکد": IGNORE,
}
MARKET_COLUMNS = {
    "digikala": {
        "کمیسیون دیجی کالا": "commission_rate",
        "هزینه ارسال دیجی کالا": "shipping",
        "قیمت فروش دیجی": "current_price",
    },
    "snapp_shop": {
        "کمیسیون اسنپ": "commission_rate",
        "هزینه ارسال اسنپ شاپ": "shipping",
        "قیمت فروش اسنپ": "current_price",
    },
}
# These are calculated outputs/statuses, not acquisition costs or live selling prices.
OUTPUT_COLUMNS = {
    "قیمت سایت",
    "سر به سر دیجی",
    "سر به سر اسنپ",
    "حداقل مارجین ۱۰ اسنپ",
    "حداقل مارجین ۵  دیجی",
    "وضعیت دیجی",
    "وضعیت اسنپ",
    "قیمت درست دیجی",
    "قیمت درست اسنپ تومان",
}


def available_markets(headers: list[str]) -> list[str]:
    keys = {header_key(h) for h in headers}
    return [m for m, names in MARKET_COLUMNS.items() if keys & {header_key(n) for n in names}]


def suggest_mapping(headers: list[str], marketplace: str | None = None) -> dict[str, str]:
    aliases = {header_key(k): v for k, v in ALIASES.items()}
    for names in MARKET_COLUMNS.values():
        aliases.update({header_key(k): IGNORE for k in names})
    aliases.update({header_key(k): IGNORE for k in OUTPUT_COLUMNS})
    if marketplace:
        aliases.update({header_key(k): v for k, v in MARKET_COLUMNS.get(marketplace, {}).items()})
    mapping = {h: h if h in Product.model_fields else aliases.get(header_key(h), UNMAPPED) for h in headers}
    # This catalog's unique text code is safer than its incomplete supplier product IDs.
    if "کد" in headers and "کد کالا" in headers:
        mapping["کد کالا"] = IGNORE
    return mapping


def map_rows(rows: list[dict], mapping: dict[str, str], conversions: dict | None = None) -> list[dict]:
    if any(v == UNMAPPED for v in mapping.values()):
        raise ValueError("Resolve the highlighted column mappings before calculating")
    active = [v for v in mapping.values() if v != IGNORE]
    if len(set(active)) != len(active):
        raise ValueError("DUPLICATE_COLUMNS: choose unique mappings")
    if "purchase_cost" not in active:
        raise ValueError("Map a purchase cost column before calculating")
    result = []
    for row in rows:
        record = {}
        for key, value in row.items():
            field = mapping[key]
            if field == IGNORE:
                continue
            conversion = (conversions or {}).get(key, "As entered")
            if conversion != "As entered":
                try:
                    if conversion == "TOMAN → IRR":
                        value = number(value) * 10
                    elif conversion == "Percentage number":
                        # Explicit percent text already represents a fraction.
                        value = number(value) if "%" in str(value).replace("٪", "%") else number(value) / 100
                    else:
                        raise ValueError("Unknown conversion")
                except ValueError:
                    pass  # Preserve invalid/blank cells for individual product validation.
            record[field] = value
        result.append(record)
    return result
