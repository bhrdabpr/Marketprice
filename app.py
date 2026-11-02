"""Local-first UI. No uploaded data is cached globally or sent to external APIs."""

import hashlib

import pandas as pd
import streamlit as st

from marketprice.batch import COST_FIELDS, process
from marketprice.config import load_profiles
from marketprice.flexible import calculate_catalog
from marketprice.importing import IGNORE, UNMAPPED, available_markets, map_rows, suggest_mapping
from marketprice.io import read_upload, workbook_bytes
from marketprice.labels import label
from marketprice.models import CURRENCIES, Product
from marketprice.samples import sample_rows
from marketprice.validation import number

st.set_page_config(page_title="MarketPrice • pricing you can explain", page_icon="◈", layout="wide")
st.markdown(
    """<style>
.stApp {background:#f1f2f4;color:#111111;}
[data-testid="stSidebar"] {background:#e5e7eb;}
.stButton, .stDownloadButton {display:flex;justify-content:center;}
.stButton button, .stDownloadButton button {background:#2563eb;color:#ffffff;border:0;border-radius:8px;min-height:44px;}
.stButton button p, .stDownloadButton button p {color:#ffffff;}
.stButton button:hover, .stDownloadButton button:hover {background:#1d4ed8;color:#ffffff;}
</style>""",
    unsafe_allow_html=True,
)
st.title("MarketPrice")
st.caption("Know your price floor. Test your campaign. Keep the calculation trail.")
st.info(
    "Example marketplace profiles • Enter your own verified fees and tax rules • All calculations run on this server"
)
profiles = load_profiles()
with st.sidebar:
    st.header("Calculation settings")
    selected = st.selectbox("Marketplace for files without a marketplace column", list(profiles))
    flexible = st.checkbox("Flexible catalog (only your included costs apply)", value=True)
    currency = st.selectbox(
        "Currency for files without a currency column", list(CURRENCIES), index=list(CURRENCIES).index("IRR")
    )
    target = st.text_input("Target margin for files without a target column", "10%")
    st.caption(
        "Flexible mode: absent costs/taxes are inapplicable (zero). Included columns need values for every product. Fixed tax amount → other_fixed; seller tax percentage → transaction_tax_rate. No current price → price floor only."
    )
    locale = st.selectbox("Number format", ["en", "fa", "comma"])
    margins_text = st.text_input("Additional margin scenarios (semicolon separated)", "15%; 25%")
    discount_text = st.text_input("Campaign discounts (semicolon separated)", "5%; 10%; 15%; 20%")
    kind = st.selectbox("Discount type", ["percent", "fixed"])
    share = st.text_input("Platform-funded share", "0%")
    override = st.checkbox("Explicitly allow unsafe campaign simulations (still labeled unsafe)", value=False)
    rtl = st.checkbox("راست به چپ / RTL labels")
    if rtl:
        st.markdown("<style>h1,h2,h3,p {direction:rtl;text-align:right}</style>", unsafe_allow_html=True)
    with st.expander("Seasonal offers (پیشنهادهای مناسبتی)"):
        event_names = st.multiselect(
            "Events (مناسبت ها)",
            ["Black Friday (جمعه سیاه)", "Christmas (کریسمس)", "Nowruz (نوروز)", "Yalda (یلدا)"],
            default=["Black Friday (جمعه سیاه)", "Nowruz (نوروز)"],
        )
        events = []
        for event_name in event_names:
            event_margin = st.text_input(event_name + " — margin (حاشیه سود)", "5%")
            event_cost = st.text_input(event_name + " — extra cost per item (هزینه اضافی هر واحد)", "0")
            events.append((event_name, event_margin, event_cost))
        st.caption(
            "Each event uses your own fees and margin. Identical settings produce identical offers. Suggestions use actual current prices, with no invented reference-price increases. Extra costs use each row's currency."
        )
    st.caption("Analysis concerns unit prices and margins only (تحلیل قیمت و سود هر واحد).")
st.download_button(
    "Download sample input",
    workbook_bytes({"Products": sample_rows()}),
    "sample_input.xlsx",
    on_click="ignore",
)
upload = st.file_uploader("Upload products (.xlsx or UTF-8 .csv)", type=["xlsx", "csv"])
st.caption(
    "25 MiB / 100,000 rows maximum. Required blanks cause errors; enter 0 only when confirmed. Samples include one intentional error."
)
if upload is not None:
    try:
        raw_bytes = upload.getvalue()
        initial = read_upload(raw_bytes, upload.name, preserve_headers=True)
        markets = available_markets(list(initial[0]))
        source_market = st.selectbox("Marketplace columns to use", markets) if markets else None
        if source_market:
            st.info(
                "This file contains marketplace-specific columns. Only the selected marketplace's selling price, commission and shipping are used. Previous calculated prices and status columns are excluded; review the mapping below."
            )
        suggested = suggest_mapping(list(initial[0]), source_market)
        suggested = {k: IGNORE if v == "quantity" else v for k, v in suggested.items()}
        with st.expander("Column mapping", expanded=True):
            st.caption(
                "Review the suggested fields. Choose a field for unknown headers, or explicitly Ignore column. Amounts and percentage rates are different fields."
            )
            mapping = {}
            conversions = {}
            for column in initial[0]:
                choices = [UNMAPPED] + [f for f in Product.model_fields if f != "quantity"] + [IGNORE]
                samples = [str(row.get(column))[:80] for row in initial[:3]]
                st.caption("Examples: " + " | ".join(samples))
                mapping[column] = st.selectbox(
                    column,
                    choices,
                    index=choices.index(suggested[column]),
                    format_func=lambda field: label(field) if field in Product.model_fields else field,
                    key="map_" + hashlib.sha256(raw_bytes).hexdigest()[:12] + str(source_market) + column,
                )
                field = mapping[column]
                unit_options = ["As entered"]
                if field.endswith("_rate") or "margin" in field or field == "max_discount":
                    unit_options.append("Percentage number")
                elif (
                    field in Product.model_fields
                    and field
                    not in {
                        "sku",
                        "name",
                        "category",
                        "quantity",
                        "marketplace",
                        "currency",
                        "tax_mode",
                        "recommendation_rule",
                        "fee_tax_recoverable",
                    }
                    and currency == "IRR"
                ):
                    unit_options.append("TOMAN → IRR")
                if len(unit_options) > 1:
                    conversions[column] = st.selectbox(
                        "Value format: " + column,
                        unit_options,
                        key="unit_"
                        + hashlib.sha256(raw_bytes).hexdigest()[:12]
                        + str(source_market)
                        + column,
                    )
            confirmed_mapping = st.checkbox(
                "I reviewed the column meanings, ignored columns and units",
                value=False,
                key="confirm_"
                + hashlib.sha256(
                    repr((raw_bytes[:128], mapping, conversions, source_market)).encode()
                ).hexdigest(),
            )
        pending = [k for k, v in mapping.items() if v == UNMAPPED]
        if pending:
            st.warning("Choose a field or Ignore column for: " + ", ".join(pending))
            st.stop()
        mapped = map_rows(initial, mapping, conversions)
        if source_market:
            mapped = [{**row, "marketplace": source_market} for row in mapped]
        default_tax = st.text_input("Seller tax expense rate (only when no tax column exists)", "0%")
        st.caption(
            "Seller expense as a percentage of selling price, separate from collected VAT. If no tax column exists, enter the rate here. Zero means no seller tax expense."
        )
        if "transaction_tax_rate" not in mapped[0]:
            mapped = [{**row, "transaction_tax_rate": default_tax} for row in mapped]
        if "marketplace" not in mapped[0]:
            mapped = [{**row, "marketplace": selected} for row in mapped]
        scope_enabled = st.checkbox(
            "Configure applicable costs for this workbook", value=False, disabled=flexible
        )
        applicable = (
            st.multiselect(
                "Applicable cost fields (all present columns are still validated)",
                sorted(COST_FIELDS),
                default=sorted(set(mapped[0]) & COST_FIELDS),
            )
            if scope_enabled and not flexible
            else None
        )
        if scope_enabled:
            st.caption(
                "Unselected cost fields are treated as zero only when their columns are absent. Present blank cells still cause product-level errors. Tax settings and purchase cost remain required."
            )
        st.subheader("Input preview")
        st.dataframe(pd.DataFrame(mapped[:30]).astype(str), hide_index=True)
        settings = (
            flexible,
            currency,
            target,
            selected,
            locale,
            margins_text,
            discount_text,
            kind,
            share,
            override,
            mapping,
            conversions,
            confirmed_mapping,
            events,
            source_market,
            default_tax,
            applicable,
        )
        fingerprint = hashlib.sha256(raw_bytes + repr(settings).encode()).hexdigest()
        if st.session_state.get("fingerprint") != fingerprint:
            st.session_state.pop("result", None)
            st.session_state.pop("download", None)
        if st.button("Validate and calculate", type="primary", disabled=not confirmed_mapping):
            margins = tuple(number(x.strip(), locale) for x in margins_text.split(";") if x.strip())
            discounts = tuple(number(x.strip(), locale) for x in discount_text.split(";") if x.strip())
            bar = st.progress(0.0, text="Validating and calculating independent products")
            calculator = calculate_catalog if flexible else process
            mode_settings = (
                {"currency": currency, "target_margin": target, "marketplace": selected}
                if flexible
                else {"applicable_costs": set(applicable) if applicable is not None else None}
            )
            result = calculator(
                mapped,
                **mode_settings,
                profiles=profiles,
                locale=locale,
                margins=margins,
                discounts=discounts,
                platform_share=number(share, locale),
                campaign_kind=kind,
                override=override,
                progress=lambda value: bar.progress(value),
                events=tuple((name, number(m, locale), number(cost, locale)) for name, m, cost in events),
            )
            result["Assumptions"].append(
                {
                    "setting": "Source column mapping",
                    "value": {
                        "mapping": mapping,
                        "conversions": conversions,
                        "selected_marketplace": source_market,
                        "seller_tax_default": default_tax,
                        "policy": "Marketplace columns kept separate; ignored source columns are listed in mapping.",
                    },
                }
            )
            with st.spinner("Preparing audited workbook…"):
                st.session_state["download"] = workbook_bytes(result)
            st.session_state["result"] = result
            st.session_state["fingerprint"] = fingerprint
            bar.progress(1.0, text="Complete — results ready")
        if "result" in st.session_state:
            result = st.session_state["result"]
            cols = st.columns(4)
            for col, item in zip(cols, result["Summary"][:3]):
                col.metric(item["metric"], item["value"])
            eligible = {r["sku"] for r in result["Campaign_Simulations"] if r["safe"]}
            cols[3].metric("SKUs with a safe campaign", len(eligible))
            st.download_button(
                "Download results workbook",
                st.session_state["download"],
                "marketprice_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                on_click="ignore",
                type="primary",
            )
            tabs = st.tabs(["Products", "Recommendations", "Campaigns", "Errors & warnings", "Audit"])
            for tab, sheet in zip(
                tabs[:3], ["Product_Calculations", "Price_Recommendations", "Campaign_Simulations"]
            ):
                with tab:
                    data = [
                        {k: str(v) for k, v in row.items() if not k.startswith("original_")}
                        for row in result[sheet][:1000]
                    ]
                    st.dataframe(pd.DataFrame(data).rename(columns=label), hide_index=True)
                    st.caption("Preview limited to 1,000 records. Download includes every input row.")
            with tabs[0]:
                values = [
                    float(r["margin"]) for r in result["Product_Calculations"] if r.get("margin") is not None
                ]
                if values:
                    buckets = pd.cut(
                        pd.Series(values),
                        [-float("inf"), 0, 0.1, 0.2, 0.3, float("inf")],
                        labels=["Loss", "0–10%", "10–20%", "20–30%", "30%+"],
                    ).value_counts(sort=False)
                    st.bar_chart(buckets)
            with tabs[3]:
                st.dataframe(pd.DataFrame(result["Errors"]), hide_index=True)
                st.dataframe(pd.DataFrame(result["Warnings"]), hide_index=True)
            st.subheader("Price analysis (تحلیل قیمت)")
            st.caption(
                "Compare your selected margins: Increase / افزایش, Decrease / کاهش, Keep / حفظ قیمت. A higher unit margin does not prove higher total profit; demand is not estimated."
            )
            st.dataframe(
                pd.DataFrame(result["Price_Analysis"][:1000]).astype(str).rename(columns=label),
                hide_index=True,
            )
            st.subheader("Seasonal campaign offers (پیشنهاد کمپین مناسبتی)")
            st.caption(
                "SAFE means the configured margin and discount cap are met. NO_SAFE_OFFER means no permitted discount meets them. Discounts are fractions (0.10 = 10%). The export includes every row."
            )
            st.dataframe(
                pd.DataFrame(result["Seasonal_Campaigns"][:1000]).astype(str).rename(columns=label),
                hide_index=True,
            )
            with tabs[4]:
                st.json(result["Assumptions"])
                st.caption(
                    "Exact inputs, versions, rules and row identities are included in the workbook. No cross-currency totals."
                )
    except ValueError as exc:
        st.error(str(exc))
    except Exception:  # noqa: BLE001 - UI boundary must suppress sensitive internals
        st.error(
            "Processing failed safely. Check the input and configuration; no recommendation is available for this run."
        )
        st.session_state.pop("result", None)
        st.session_state.pop("download", None)
else:
    st.subheader("From workbook to defensible prices")
    a, b, c = st.columns(3)
    a.markdown("**1 · Validate**\n\nMap columns and catch unknown costs before pricing.")
    b.markdown("**2 · Calculate**\n\nSeparate contribution, collected tax, and seller expenses.")
    c.markdown("**3 · Decide**\n\nCompare margin targets and funded campaigns, then export the audit trail.")
    st.markdown(
        "**Privacy:** uploads and results stay in server session memory. Reset the session to clear them. Local launch binds to localhost."
    )
