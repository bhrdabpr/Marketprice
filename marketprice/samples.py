from .models import FIXED_FIELDS


def sample_row(sku="GOLDEN-001") -> dict:
    return {
        "sku": sku,
        "name": "Sample headphones / هدفون",
        "marketplace": "generic",
        "category": "general",
        "currency": "USD",
        "current_price": "140",
        "purchase_cost": "70",
        **{f: "0" for f in FIXED_FIELDS},
        "shipping": "8",
        "other_fixed": "2",
        "commission_rate": "10%",
        "commission_fixed": "0",
        "payment_rate": "2%",
        "payment_fixed": "0",
        "other_rate": "0",
        "transaction_tax_rate": "0",
        "tax_rate": "0",
        "tax_mode": "exclusive",
        "input_tax_credit": "0",
        "fee_tax_rate": "0",
        "fee_tax_recoverable": "false",
        "target_margin": "20%",
        "minimum_margin": "10%",
        "campaign_margin": "10%",
        "max_discount": "30%",
        "increment": "0.01",
        "recommendation_rule": "floor",
    }


def sample_rows():
    return [
        sample_row(),
        {
            **sample_row("FA-002"),
            "name": "کالای نمونه",
            "currency": "TOMAN",
            "purchase_cost": "۷۰۰۰۰۰",
            "shipping": "۸۰۰۰۰",
            "other_fixed": "۲۰۰۰۰",
            "current_price": "۱۴۰۰۰۰۰",
            "increment": "1000",
        },
        {**sample_row("ERROR-003"), "shipping": ""},
    ]
