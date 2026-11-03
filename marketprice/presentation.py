"""Display-only localization: never changes calculation inputs or exported amounts."""

from decimal import Decimal

import pandas as pd

from .i18n import translate
from .labels import PERSIAN, label
from .models import FIXED_FIELDS
from .precision import financial

DIGITS = str.maketrans("0123456789,.%", "۰۱۲۳۴۵۶۷۸۹٬٫٪")
MONEY_FIELDS = set(FIXED_FIELDS) | {
    "competitor_delivered_price",
    "delivered_price_gap",
    "purchase_cost",
    "current_price",
    "recommended_price",
    "normal_price",
    "margin_floor",
    "floor",
    "break_even",
    "price",
    "customer_gross",
    "subsidy",
    "revenue",
    "tax_collected",
    "cogs",
    "fixed_expenses",
    "commission",
    "payment",
    "other",
    "fee_tax",
    "transaction_tax",
    "profit",
    "price_change",
    "campaign_price",
    "campaign_cost",
    "baseline_unit_profit",
    "commission_fixed",
    "payment_fixed",
    "input_tax_credit",
    "competitor_price",
    "price_ceiling",
    "price_minimum",
    "increment",
    "amount",
    "expected_amount",
    "impact",
    "contribution",
    "contribution_per_sold_unit",
    "contribution_before_unallocated_costs",
    "historical_cost",
    "replacement_cost",
    "replacement_contribution",
    "net_revenue",
    "net_profit_events",
    "sales_revenue",
    "refunds",
    "marketplace_advertising",
    "unallocated_net_events",
    "expected_payout",
    "paid",
    "difference",
    "actual_discount",
    "requested_discount",
    "profit_change",
    "total_cost",
    "other_variable",
    "fee_tax_credit",
}
EXTRA_LABELS = {
    "rejection_reasons": "دلیل رد شواهد",
    "evidence_status": "وضعیت شواهد",
    "review": "نتیجه بررسی",
    "buy_box_prediction": "پیش‌بینی بای‌باکس",
    "competitor_delivered_price": "قیمت تحویلی رقیب",
    "delivered_price_gap": "فاصله قیمت تحویلی",
    "observed_at": "زمان مشاهده",
    "source_url": "منبع مشاهده",
    "rejected_observations": "مشاهدات ردشده",

    "decision": "اقدام پیشنهادی",
    "row": "ردیف فایل",
    "problem": "ستون‌های نیازمند اصلاح",
    "source_row": "ردیف منبع",
    "currency": "واحد پول",
    "order_id": "شماره سفارش",
    "settlement_id": "شماره تسویه",
    "transaction_id": "شماره تراکنش",
    "units_sold": "تعداد فروش",
    "contribution": "سود پس از هزینه‌های ثبت‌شده",
    "contribution_per_sold_unit": "سود هر واحد فروخته‌شده",
    "contribution_before_unallocated_costs": "سود پیش از هزینه‌های مشترک",
    "historical_cost": "بهای خرید در زمان فروش",
    "replacement_cost": "هزینه جایگزینی امروز",
    "replacement_contribution": "سود با هزینه جایگزینی",
    "net_revenue": "درآمد خالص",
    "net_profit_events": "خالص مبالغ درآمد و هزینه",
    "sales_revenue": "درآمد فروش",
    "refunds": "مبلغ بازپرداخت",
    "marketplace_advertising": "هزینه تبلیغات بازار",
    "unallocated_net_events": "مبالغ تخصیص‌نیافته",
    "expected_payout": "تسویه مورد انتظار",
    "paid": "مبلغ واریزشده",
    "difference": "اختلاف",
    "overdue": "سررسید گذشته",
    "days_first_sale_to_last_payout": "روز از اولین فروش تا آخرین واریز",
    "payment_types": "روش پرداخت",
    "source_rows": "ردیف‌های منبع",
    "cost_sources": "منابع هزینه",
    "campaign": "کمپین",
    "phase": "دوره",
    "note": "توضیح",
    "skus": "شناسه کالاها",
    "code": "نوع خطا",
    "field": "ستون",
    "explanation": "توضیح خطا",
    "correction": "روش اصلاح",
    "error": "خطا",
    "source": "منبع",
    "floor": "کف قیمت هدف",
    "price": "قیمت",
    "customer_gross": "مبلغ پرداخت مشتری",
    "revenue": "درآمد",
    "cogs": "بهای تمام‌شده خرید",
    "fixed_expenses": "هزینه‌های ثابت",
    "commission": "کمیسیون",
    "payment": "هزینه پرداخت",
    "tax_collected": "مالیات دریافتی",
    "subsidy": "کمک‌هزینه بازار",
    "required_sales_multiplier": "ضریب فروش لازم برای حفظ سود",
    "decision_note": "نکته تصمیم‌گیری",
    "objective": "هدف محاسبه",
    "platform_share": "سهم بازار از تخفیف",
    "volume_note": "توضیح تعداد فروش",
    "safe": "شرایط سود رعایت شده",
}
EXTRA_LABELS.update(
    {
        "other_variable": "سایر هزینه‌های متغیر",
        "total_cost": "مجموع هزینه",
        "fee_tax_credit": "اعتبار مالیات کارمزد",
        "fee_tax": "مالیات کارمزد",
        "transaction_tax": "مالیات هزینه فروشنده",
        "markup": "سود نسبت به هزینه",
        "profit_change": "تغییر سود",
        "requested_discount": "تخفیف مورد بررسی",
        "actual_discount": "مبلغ تخفیف",
        "discount_kind": "نوع تخفیف",
        "approved": "مجاز در تنظیمات",
        "override": "اجازه بررسی خارج از حد",
        "warning": "هشدار",
        "explanation": "توضیح",
        "decision_note": "پیش از تصمیم بررسی کنید",
        "max_break_even_discount": "بیشترین تخفیف تا سربه‌سر",
        "max_minimum_margin_discount": "بیشترین تخفیف با حفظ حد سود",
        "discount_limit_note": "توضیح سقف تخفیف",
        "current_price_status": "وضعیت قیمت فعلی",
    }
)

VALUES = {
    "NOT_PREDICTED": "پیش‌بینی نشده",
    "ADD_COMPARABLE_OFFER": "پیشنهاد همسان و معتبر اضافه کنید",
    "CONFIRM_COSTS_OR_MARGIN": "هزینه‌ها یا حاشیه سود نیازمند تأیید است",
    "WITHIN_OBSERVED_PRICE": "در محدوده قیمت مشاهده‌شده",
    "ABOVE_OBSERVED_PRICE": "بالاتر از قیمت مشاهده‌شده",
    "REVIEWED_SELLER_INPUT": "بررسی‌شده بر اساس داده فروشنده",
    "REJECTED": "شواهد معتبر نیست",

    "VALID": "معتبر",
    "INVALID": "نیازمند اصلاح",
    "KEEP": "حفظ قیمت",
    "INCREASE": "بررسی افزایش قیمت",
    "REVIEW_DECREASE": "بررسی کاهش قیمت",
    "SET_PRICE": "تعیین قیمت اولیه",
    "CONFIRM_COSTS": "تکمیل یا تأیید هزینه‌ها",
    "FIX_PRODUCT": "اصلاح اطلاعات کالا",
    "REVIEW_MARGIN": "بررسی حاشیه سود",
    "REVIEW_LOSS": "بررسی زیان",
    "VERIFY_ESTIMATES": "بررسی هزینه‌های تخمینی",
    "CONFIRMED_INPUTS": "ورودی‌های تأییدشده",
    "MISSING": "اطلاعات ناقص",
    "ESTIMATED": "تخمینی",
    "SAFE": "در محدوده سود تعیین‌شده",
    "NO_SAFE_OFFER": "تخفیف مناسب یافت نشد",
    "MATCHED": "تطبیق دارد",
    "REVIEW": "نیازمند بررسی",
    "INCOMPLETE": "ناقص",
    "UNALLOCATED": "تخصیص‌نیافته",
    "REVIEW_SETTLEMENT": "بررسی اختلاف تسویه",
    "EXPECTED_AMOUNT_DIFFERS": "بررسی اختلاف مبلغ",
    "FIX_SOURCE_ROW": "اصلاح ردیف منبع",
    "MISSING_DATED_COST": "ثبت هزینه تاریخ‌دار",
    "ORDER_SALE_MISSING": "سفارش بدون سابقه فروش",
    "UNMATCHED_SETTLEMENT": "تعیین تسویه مرتبط",
    "REVIEW_UNALLOCATED": "تخصیص هزینه مشترک",
    "REALIZED_LOSS": "بررسی فروش زیان‌ده",
    "ORDER_SKU_MISMATCH": "شناسه کالا با سفارش سازگار نیست",
    "AMBIGUOUS_CAMPAIGN_ALLOCATION": "بررسی انتساب هزینه به کمپین",
    "before": "پیش از کمپین",
    "during": "حین کمپین",
    "after": "پس از کمپین",
    "cash": "نقدی",
    "credit": "اعتباری",
    "unknown": "نامشخص",
}


def field_label(field, language="en"):
    if language == "fa":
        return EXTRA_LABELS.get(field, PERSIAN.get(field, field.replace("_", " ")))
    # English view is English-only; canonical export keys stay unchanged.
    return label(field).split(" (")[0]


@financial
def display_value(
    field, value, *, currency=None, display_currency="original", language="en", persian_digits=False
):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return ("بله" if value else "خیر") if language == "fa" else ("Yes" if value else "No")
    if field == "currency":
        shown = display_currency if currency in {"IRR", "TOMAN"} and display_currency != "original" else value
        return {"IRR": "ریال", "TOMAN": "تومان"}.get(shown, shown) if language == "fa" else shown
    if isinstance(value, (int, Decimal, float)):
        number = Decimal(str(value))
        if not number.is_finite():
            return "—"
        if (
            field in MONEY_FIELDS
            and currency in {"IRR", "TOMAN"}
            and display_currency in {"IRR", "TOMAN"}
            and currency != display_currency
        ):
            number *= Decimal(10) if display_currency == "IRR" else Decimal(".1")
        if (
            "margin" in field
            and field != "margin_floor"
            or field.endswith("_rate")
            or field
            in {"suggested_discount", "max_discount", "platform_share", "max_break_even_discount", "markup"}
        ):
            text = f"{number * 100:,.2f}%"
        elif field == "required_sales_multiplier":
            text = f"{number:,.4f}".rstrip("0").rstrip(".")
        else:
            text = format(number, ",f")
            if "." in text:
                text = text.rstrip("0").rstrip(".")
        return text.translate(DIGITS) if persian_digits else text
    if (
        field == "field"
        or field in {"missing_costs", "estimated_costs", "confirmed_zero_costs"}
        and isinstance(value, str)
    ):
        return field_label(value, language)
    if isinstance(value, list):
        return "، ".join(
            str(display_value(field, v, language=language, persian_digits=persian_digits)) for v in value
        )
    return translate(VALUES.get(str(value), str(value)) if language == "fa" else str(value), language)


def preview(records, *, language="en", display_currency="original", persian_digits=False):
    records = [{k: v for k, v in r.items() if not k.startswith("original_")} for r in records]
    if language == "fa":
        for row in records:
            code = row.get("code", "")
            if "correction" in row and row.get("field"):
                field = field_label(row["field"], language)
                row["correction"] = f"مقدار «{field}» را بررسی کنید؛ برای هزینه واقعاً صفر، عدد صفر بنویسید."
                if code.startswith("MISSING_"):
                    row["explanation"] = f"مقدار «{field}» وارد نشده است."
                elif code == "DUPLICATE_SKU":
                    row["explanation"] = "شناسه کالا تکراری است؛ هر کالا باید شناسه یکتا داشته باشد."
                else:
                    row["explanation"] = (
                        f"مقدار «{field}» با نوع یا محدوده مجاز سازگار نیست؛ جزئیات فنی در گزارش کامل ثبت شده است."
                    )
    frame = pd.DataFrame(
        [
            {
                field_label(k, language): display_value(
                    "requested_discount_rate"
                    if k == "requested_discount" and r.get("discount_kind") == "percent"
                    else k,
                    v,
                    currency=r.get("currency"),
                    display_currency=display_currency,
                    language=language,
                    persian_digits=persian_digits,
                )
                for k, v in r.items()
            }
            for r in records
        ]
    )
    return frame[frame.columns[::-1]] if language == "fa" else frame


def filter_results(result, status="all"):
    """Filter every product-linked section using source row, preserving exported results."""
    if status == "all":
        return result
    wanted = "VALID" if status == "valid" else "INVALID"
    rows = {r["row"] for r in result["Product_Calculations"] if r["status"] == wanted}
    return {
        name: [r for r in records if "row" not in r or r["row"] in rows] for name, records in result.items()
    }
