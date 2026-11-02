"""Local-first UI. No uploaded data is cached globally or sent to external APIs."""

import hashlib

import pandas as pd
import streamlit as st

from marketprice.batch import COST_FIELDS, process
from marketprice.config import load_profiles
from marketprice.io import read_upload, workbook_bytes
from marketprice.models import Product
from marketprice.samples import sample_rows
from marketprice.validation import number

st.set_page_config(page_title="MarketPrice • pricing you can explain", page_icon="◈", layout="wide")
st.title("MarketPrice")
st.caption("Know your price floor. Test your campaign. Keep the calculation trail.")
st.info(
    "Example marketplace profiles • Enter your own verified fees and tax rules • All calculations run on this server"
)
profiles = load_profiles()
with st.sidebar:
    st.header("Calculation settings")
    selected = st.selectbox("Marketplace for files without a marketplace column", list(profiles))
    locale = st.selectbox("Number format", ["en", "fa", "comma"])
    margins_text = st.text_input("Additional margin scenarios (semicolon separated)", "15%; 25%")
    discount_text = st.text_input("Campaign discounts (semicolon separated)", "5%; 10%; 15%; 20%")
    kind = st.selectbox("Discount type", ["percent", "fixed"])
    share = st.text_input("Platform-funded share", "0%")
    override = st.checkbox("Explicitly allow unsafe campaign simulations (still labeled unsafe)", value=False)
    rtl = st.checkbox("راست به چپ / RTL labels")
    if rtl:
        st.markdown("<style>h1,h2,h3,p {direction:rtl;text-align:right}</style>", unsafe_allow_html=True)
    st.caption("No income tax or withholding model. Inventory is not a sales forecast.")
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
        initial = read_upload(raw_bytes, upload.name)
        with st.expander("Column mapping", expanded=False):
            st.caption("Select the canonical field for each source column. Duplicate mappings are rejected.")
            mapping = {}
            for column in initial[0]:
                choices = list(Product.model_fields)
                if column not in choices:
                    choices = [column] + choices
                mapping[column] = st.selectbox(
                    column, choices, index=choices.index(column), key="map_" + column
                )
        # Import first, then map the normalized header names displayed above.
        mapped = [dict(zip([mapping[k] for k in row], row.values())) for row in initial]
        if len(set(mapping.values())) != len(mapping):
            raise ValueError("DUPLICATE_COLUMNS: choose unique mappings")
        if "marketplace" not in mapped[0]:
            mapped = [{**row, "marketplace": selected} for row in mapped]
        scope_enabled = st.checkbox("Configure applicable costs for this workbook", value=False)
        applicable = (
            st.multiselect(
                "Applicable cost fields (all present columns are still validated)",
                sorted(COST_FIELDS),
                default=sorted(set(mapped[0]) & COST_FIELDS),
            )
            if scope_enabled
            else None
        )
        if scope_enabled:
            st.caption(
                "Unselected cost fields are treated as zero only when their columns are absent. Present blank cells still cause product-level errors. Tax settings and purchase cost remain required."
            )
        st.subheader("Input preview")
        st.dataframe(pd.DataFrame(mapped[:30]).astype(str), hide_index=True)
        settings = (selected, locale, margins_text, discount_text, kind, share, override, mapping, applicable)
        fingerprint = hashlib.sha256(raw_bytes + repr(settings).encode()).hexdigest()
        if st.session_state.get("fingerprint") != fingerprint:
            st.session_state.pop("result", None)
            st.session_state.pop("download", None)
        if st.button("Validate and calculate", type="primary"):
            margins = tuple(number(x.strip(), locale) for x in margins_text.split(";") if x.strip())
            discounts = tuple(number(x.strip(), locale) for x in discount_text.split(";") if x.strip())
            bar = st.progress(0.0, text="Validating and calculating independent products")
            result = process(
                mapped,
                applicable_costs=set(applicable) if applicable is not None else None,
                profiles=profiles,
                locale=locale,
                margins=margins,
                discounts=discounts,
                platform_share=number(share, locale),
                campaign_kind=kind,
                override=override,
                progress=lambda value: bar.progress(value),
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
                    st.dataframe(pd.DataFrame(data), hide_index=True)
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
