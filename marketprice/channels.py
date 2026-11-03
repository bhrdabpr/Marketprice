"""Sales-channel presentation and column scope, not official fee schedules."""

from .importing import IGNORE, TOKENS, header_key
from .models import Product

CHANNELS = {
    "custom": ("Personal website / custom", "سایت شخصی / تنظیمات دلخواه"),
    "digikala": ("Digikala", "دیجی‌کالا"),
    "snapp_shop": ("Snapp Shop", "اسنپ‌شاپ"),
    "tapsi_shop": ("Tapsi Shop", "تپسی‌شاپ"),
    "amazon": ("Amazon", "آمازون"),
    "ebay": ("eBay", "ای‌بی"),
    "shopify": ("Shopify", "شاپیفای"),
    "woocommerce": ("WooCommerce", "ووکامرس"),
}
COMMON = [
    "sku",
    "name",
    "purchase_cost",
    "current_price",
    "shipping",
    "overhead",
    "packaging",
    "transaction_tax_rate",
    "tax_rate",
    "other_fixed",
    "target_margin",
    "currency",
]
SPECIAL = {
    "custom": ["payment_rate", "payment_fixed", "advertising", "software", "customer_support"],
    "digikala": ["commission_rate", "commission_fixed", "fulfillment", "warehouse", "expected_return_cost"],
    "snapp_shop": ["commission_rate", "commission_fixed", "financing", "expected_return_cost"],
    "tapsi_shop": ["commission_rate", "commission_fixed", "financing", "expected_return_cost"],
    "amazon": [
        "commission_rate",
        "commission_fixed",
        "fulfillment",
        "warehouse",
        "inbound_freight",
        "advertising",
        "expected_return_cost",
    ],
    "ebay": [
        "commission_rate",
        "commission_fixed",
        "payment_rate",
        "payment_fixed",
        "currency_conversion",
        "advertising",
    ],
}


def channel_label(channel, language="en"):
    return CHANNELS.get(channel, (channel, channel))[language == "fa"]


def column_market(column):
    key = " " + header_key(column) + " "
    for market, tokens in TOKENS.items():
        if any(" " + header_key(token) + " " in key for token in tokens):
            return market
    return None


def excluded_columns(headers, selected):
    return [h for h in headers if column_market(h) not in (None, selected)]


def matching_fields(selected, *, advanced=False, suggested=None):
    if advanced:
        return [f for f in Product.model_fields if f != "quantity"]
    fields = list(dict.fromkeys(COMMON + SPECIAL.get(selected, SPECIAL["custom"])))
    if suggested in Product.model_fields and suggested != "quantity" and suggested not in fields:
        fields.append(suggested)
    return fields


def scoped_mapping(headers, selected, mapping):
    result = dict(mapping)
    for h in excluded_columns(headers, selected):
        result[h] = IGNORE
    if selected in {"custom", "shopify", "woocommerce"}:
        for h in headers:
            if header_key(h) == "قیمت سایت":
                result[h] = "current_price"
    return result
