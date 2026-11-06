"""Observed price / velocity map; no inferred competitor sales."""

import json

import altair as alt
import pandas as pd
import streamlit as st

from .io import json_default, read_upload
from .opportunity import compare, descriptive_fit, sales_rows
from .presentation import display_value, preview


def render_opportunity(language="en", display_currency="original", persian_digits=False):
    fa = language == "fa"

    def t(en, persian):
        return persian if fa else en

    st.subheader(t("See where each product stands", "جایگاه هر کالا را ببینید"))
    st.caption(
        t(
            "One marketplace, category and currency. Lines show group medians, not optimal prices.",
            "یک بازار، دسته و واحد پول؛ خطوط میانه گروه را نشان می‌دهند و قیمت بهینه نیستند.",
        )
    )
    template = "sku,marketplace,category,currency,price,units,previous_units,margin,target_margin\n"
    st.download_button(
        t("Download input template", "دریافت قالب داده"),
        template.encode(),
        "sales_map_template.csv",
        on_click="ignore",
    )
    upload = st.file_uploader(
        t("Sales comparison CSV", "فایل مقایسه فروش CSV"),
        type=["csv"],
        key=f"sales_map__session_{st.session_state.get('session_epoch', 0)}",
    )
    days = st.number_input(
        t("Days in each period", "تعداد روز در هر دوره"),
        min_value=1,
        max_value=366,
        value=30,
        key="sales_map_days",
    )
    st.caption(
        t(
            "Use consecutive equal periods for units and previous_units. Margins are decimals (0.20 = 20%). Blank margins stay unknown.",
            "units و previous_units برای دو دوره متوالی هم‌اندازه‌اند. حاشیه سود اعشاری است (۰٫۲۰ یعنی ۲۰٪). مقدار خالی نامشخص می‌ماند.",
        )
    )
    demo = st.checkbox(t("Explore synthetic example", "نمایش مثال ساختگی"), key="sales_map_demo")
    if not upload and not demo:
        st.info(
            t(
                "Add sales history to reveal price position, momentum and margin gaps.",
                "با ورود سابقه فروش، جایگاه قیمت، روند رشد و فاصله حاشیه سود مشخص می‌شود.",
            )
        )
        return
    try:
        if upload:
            raw = read_upload(upload.getvalue(), upload.name, preserve_headers=True)
        else:
            st.info(
                t(
                    "Synthetic illustration — not your business data.",
                    "مثال ساختگی؛ این اعداد مربوط به کسب‌وکار شما نیستند.",
                )
            )
            raw = [
                {
                    "sku": f"DEMO-{i + 1}",
                    "marketplace": "Demo",
                    "category": "Example",
                    "currency": "IRR",
                    "price": p,
                    "units": u,
                    "previous_units": old,
                    "margin": m,
                    "target_margin": "0.2",
                }
                for i, (p, u, old, m) in enumerate(
                    [
                        (100, 40, 30, "0.08"),
                        (140, 20, 25, "0.25"),
                        (180, 60, 40, "0.28"),
                        (220, 8, 10, "-0.02"),
                        (120, 55, 50, "0.18"),
                        (200, 30, 30, ""),
                    ]
                )
            ]
        records = sales_rows(raw, days)
        groups = sorted({(r["marketplace"], r["category"], r["currency"]) for r in records})
        group = st.selectbox(
            t("Comparison group", "گروه مقایسه"),
            groups,
            format_func=lambda g: " / ".join(g),
            key="sales_map_group",
        )
        results, price_mid, speed_mid = compare(
            [r for r in records if (r["marketplace"], r["category"], r["currency"]) == group]
        )
    except ValueError as exc:
        st.error(t("Check input values: ", "مقادیر فایل را بررسی کنید: ") + str(exc))
        return
    a, b, c = st.columns(3)
    def count(value):
        return display_value("count", value, persian_digits=persian_digits)

    a.metric(t("Products", "کالاها"), count(len(results)))
    b.metric(t("Growing", "دارای رشد فروش"), count(sum(r["trend"] == "Growing" for r in results)))
    c.metric(
        t("Below target / loss", "زیر حد سود / زیان"),
        count(sum(r["margin_risk"] in {"Loss", "Below target"} for r in results)),
    )
    risks = {
        "Loss": "زیان",
        "Below target": "زیر حد سود",
        "At or above target": "در حد سود یا بالاتر",
        "Unknown": "نامشخص",
    }
    shown_currency = group[2]
    price_factor = 1.0
    if group[2] in {"IRR", "TOMAN"} and display_currency in {"IRR", "TOMAN"}:
        shown_currency = display_currency
        if shown_currency != group[2]:
            price_factor = 10.0 if shown_currency == "IRR" else 0.1
    frame = pd.DataFrame(
        [
            {
                "sku": r["sku"],
                "price": float(r["price"]) * price_factor,
                "velocity": float(r["units_per_day"]),
                "risk": risks[r["margin_risk"]] if fa else r["margin_risk"],
            }
            for r in results
        ]
    )
    dots = (
        alt.Chart(frame)
        .mark_circle(size=180, opacity=0.9, stroke="white", strokeWidth=2)
        .encode(
            x=alt.X(
                "price:Q",
                title=t("Observed price", "قیمت ثبت‌شده") + " (" + shown_currency + ")",
                scale=alt.Scale(zero=False),
            ),
            y=alt.Y("velocity:Q", title=t("Units per day", "تعداد فروش روزانه")),
            color=alt.Color(
                "risk:N",
                title=t("Margin status", "وضعیت حاشیه سود"),
                legend=alt.Legend(orient="bottom", labelLimit=200, columnPadding=24),
                scale=alt.Scale(
                    domain=list(risks.values()) if fa else list(risks),
                    range=["#dc3545", "#8d4652", "#2764e7", "#8993a5"],
                ),
            ),
            tooltip=[
                alt.Tooltip("sku:N", title=t("Product", "کالا")),
                alt.Tooltip("price:Q", title=t("Price", "قیمت"), format=",.2f"),
                alt.Tooltip("velocity:Q", title=t("Units/day", "فروش روزانه"), format=".2f"),
                alt.Tooltip("risk:N", title=t("Margin status", "وضعیت سود")),
            ],
        )
    )
    vertical = (
        alt.Chart(pd.DataFrame({"mid": [float(price_mid) * price_factor]}))
        .mark_rule(color="#98a2b3", strokeDash=[5, 5])
        .encode(x="mid:Q")
    )
    horizontal = (
        alt.Chart(pd.DataFrame({"mid": [float(speed_mid)]}))
        .mark_rule(color="#98a2b3", strokeDash=[5, 5])
        .encode(y="mid:Q")
    )
    chart = dots + vertical + horizontal
    fit = None
    if st.checkbox(t("Show descriptive regression", "نمایش رگرسیون توصیفی"), key="sales_map_regression"):
        fit = descriptive_fit(results)
        if fit is None:
            st.info(t("At least three products and different prices are needed.", "حداقل سه کالا و قیمت‌های متفاوت لازم است."))
        else:
            fitted = pd.DataFrame([{"price": float(r["price"]) * price_factor, "fitted": float(fit["slope"] * r["price"] + fit["intercept"])} for r in sorted(results, key=lambda r: r["price"])])
            chart += alt.Chart(fitted).mark_line(color="#172d5d", strokeDash=[6, 4]).encode(x="price:Q", y="fitted:Q")
            r2 = "—" if fit["r_squared"] is None else f'{fit["r_squared"]:.3f}'
            st.caption(t("Association across products, not the effect of changing a price. No forecast. ", "رابطه بین کالاهاست، نه اثر تغییر قیمت یک کالا؛ پیش‌بینی فروش نیست. ") + f'n={fit["n"]} · R²={r2}')
    st.altair_chart(chart.properties(height=400), width="stretch")
    st.caption(
        t(
            "Position is relative to this group, not matched competitor offers. Margin status is not total business risk. Stock-outs and advertising can change sales; no causal forecast is made.",
            "جایگاه نسبت به همین گروه است، نه پیشنهاد همسان رقبا. وضعیت حاشیه سود، کل ریسک کسب‌وکار نیست. نبود موجودی و تبلیغات بر فروش اثر دارند؛ این نمودار پیش‌بینی علّی نیست.",
        )
    )
    st.dataframe(
        preview(results, language=language, display_currency=display_currency, persian_digits=persian_digits),
        hide_index=True,
    )
    st.download_button(
        t("Download analysis evidence", "دریافت شواهد تحلیل"),
        json.dumps(
            {
                "results": results,
                "median_price": price_mid,
                "median_units_per_day": speed_mid,
                "synthetic": not bool(upload),
                "descriptive_regression": fit,
            },
            default=json_default,
            ensure_ascii=False,
        ),
        "sales_map.json",
        on_click="ignore",
    )
