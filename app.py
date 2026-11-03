"""Local-first UI. No uploaded data is cached globally or sent to external APIs."""

import hashlib
import json
from datetime import date
from decimal import Decimal

import pandas as pd
import streamlit as st

from marketprice.approvals import approved_changes, snapshot
from marketprice.batch import COST_FIELDS, process
from marketprice.config import load_profiles
from marketprice.contracts import load_contract
from marketprice.flexible import calculate_catalog
from marketprice.importing import IGNORE, UNMAPPED, available_markets, map_rows, suggest_mapping
from marketprice.io import json_default, read_upload, workbook_bytes
from marketprice.labels import label
from marketprice.models import CURRENCIES, Product
from marketprice.operations_ui import render_operations
from marketprice.samples import sample_rows
from marketprice.templates import load_setup, save_setup
from marketprice.validation import number


def display_value(field, value):
    if isinstance(value, Decimal) and (
        "margin" in field
        or field.endswith("_rate")
        or field in {"suggested_discount", "max_discount", "platform_share"}
    ):
        return f"{value * 100:.2f}%"
    return str(value)


def preview(records):
    return pd.DataFrame([{label(k): display_value(k, v) for k, v in r.items()} for r in records])


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
workspace = st.radio(
    "Workspace (بخش برنامه)", ["Pricing (قیمت گذاری)", "Actual profit (سود واقعی)"], horizontal=True
)
if workspace == "Actual profit (سود واقعی)":
    render_operations()
    st.stop()
profiles = load_profiles()
with st.sidebar:
    st.header("Calculation settings")
    selected = st.selectbox("Marketplace for files without a marketplace column", list(profiles))
    flexible = st.checkbox("Flexible catalog (review cost confidence)", value=True)
    currency = st.selectbox(
        "Currency for files without a currency column", list(CURRENCIES), index=list(CURRENCIES).index("IRR")
    )
    target = st.text_input("Target margin for files without a target column", "10%")
    st.caption(
        "Flexible mode: absent costs/taxes produce provisional scenarios until confirmed inapplicable. Included columns need values for every product. Fixed tax amount → other_fixed; seller tax percentage → transaction_tax_rate. No current price → price floor only."
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
st.columns([1, 2, 1])[1].download_button(
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
        setup_file = st.file_uploader("Reuse saved setup (.json)", type=["json"], key="setup")
        setup = load_setup(setup_file.getvalue(), list(initial[0])) if setup_file else None
        if setup:
            saved = setup["settings"]
            currency = saved.get("currency", currency)
            target = saved.get("target_margin", target)
            selected = saved.get("marketplace", selected)
            locale = saved.get("locale", locale)
            if source_market and source_market != selected:
                raise ValueError(
                    "Saved setup belongs to another marketplace; change Marketplace columns to use above."
                )
            st.info(
                f"Saved settings active: {currency}, target {target}, marketplace {selected}, format {locale}. Remove setup to use sidebar settings."
            )
        suggested = setup["mapping"] if setup else suggest_mapping(list(initial[0]), source_market)
        suggested = {k: IGNORE if v == "quantity" else v for k, v in suggested.items()}
        setup_key = hashlib.sha256(setup_file.getvalue()).hexdigest()[:8] if setup_file else ""
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
                    key="map_"
                    + setup_key
                    + hashlib.sha256(raw_bytes).hexdigest()[:12]
                    + str(source_market)
                    + column,
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
                        index=unit_options.index(setup["conversions"].get(column, "As entered"))
                        if setup and setup["conversions"].get(column, "As entered") in unit_options
                        else 0,
                        key="unit_"
                        + setup_key
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
        default_tax = st.text_input(
            "Seller tax expense rate (only when no tax column exists)",
            setup["settings"].get("seller_tax", "0%") if setup else "0%",
            key="tax_" + setup_key,
        )
        st.caption(
            "Seller expense as a percentage of selling price, separate from collected VAT. If no tax column exists, enter the rate here. Zero means no seller tax expense."
        )
        if "transaction_tax_rate" not in mapped[0]:
            mapped = [{**row, "transaction_tax_rate": default_tax} for row in mapped]
        if "marketplace" not in mapped[0]:
            mapped = [{**row, "marketplace": selected} for row in mapped]
        omitted_confirmed = st.checkbox(
            "I confirm omitted cost categories are inapplicable or included elsewhere (zero additional cost)",
            value=setup["settings"].get("omitted_costs_confirmed", False) if setup else False,
            key="omitted_" + setup_key,
        )
        estimated_fields = st.multiselect(
            "Which included costs are estimates? (هزینه های تخمینی)",
            sorted(
                set(mapped[0])
                & (
                    COST_FIELDS
                    | {
                        "purchase_cost",
                        "transaction_tax_rate",
                        "tax_rate",
                        "fee_tax_rate",
                        "input_tax_credit",
                    }
                )
            ),
            format_func=label,
            default=[k for k, v in setup["settings"].get("cost_states", {}).items() if v == "estimated"]
            if setup
            else [],
            key="estimates_" + setup_key,
        )
        cost_states = (
            {k: v for k, v in setup["settings"].get("cost_states", {}).items() if v != "estimated"}
            if setup
            else {}
        )
        cost_states.update(dict.fromkeys(estimated_fields, "estimated"))
        if confirmed_mapping:
            st.download_button(
                "Save reusable setup (ذخیره تنظیمات)",
                save_setup(
                    list(initial[0]),
                    mapping,
                    conversions,
                    {
                        "currency": currency,
                        "target_margin": target,
                        "marketplace": source_market or selected,
                        "locale": locale,
                        "seller_tax": default_tax,
                        "omitted_costs_confirmed": omitted_confirmed,
                        "cost_states": cost_states,
                    },
                ),
                "marketprice_setup.json",
            )
        contract_file = st.file_uploader(
            "Optional dated seller rule bundle (.json)", type=["json"], key="contract"
        )
        contract_evidence = None
        if contract_file:
            contract, contract_hash = load_contract(
                contract_file.getvalue(), as_of=date.today(), currency=currency
            )
            if contract.profile.id != (source_market or selected):
                raise ValueError("Rule bundle marketplace differs from selected marketplace")
            if any(
                r.get("currency", currency) != currency
                or r.get("marketplace", selected) != contract.profile.id
                for r in mapped
            ):
                raise ValueError("Use one contract currency and marketplace per catalog")
            profiles[contract.profile.id] = contract.profile
            contract_evidence = {"sha256": contract_hash, **contract.model_dump(mode="json")}
            st.info(
                "Seller-reviewed rule bundle loaded; evidence is declared, not independently verified. Unsupported rule fields are rejected."
            )
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
            omitted_confirmed,
            estimated_fields,
            cost_states,
            contract_evidence,
        )
        fingerprint = hashlib.sha256(raw_bytes + repr(settings).encode()).hexdigest()
        if st.session_state.get("fingerprint") != fingerprint:
            st.session_state.pop("result", None)
            st.session_state.pop("download", None)
        calculate_clicked = st.columns([1, 2, 1])[1].button(
            "Validate and calculate", type="primary", disabled=not confirmed_mapping, width="stretch"
        )
        if calculate_clicked:
            margins = tuple(number(x.strip(), locale) for x in margins_text.split(";") if x.strip())
            discounts = tuple(number(x.strip(), locale) for x in discount_text.split(";") if x.strip())
            bar = st.progress(0.0, text="Validating and calculating independent products")
            calculator = calculate_catalog if flexible else process
            mode_settings = (
                {
                    "currency": currency,
                    "target_margin": target,
                    "marketplace": selected,
                    "omitted_costs_confirmed": omitted_confirmed,
                    "cost_states": cost_states,
                }
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
            if contract_evidence:
                result["Assumptions"].append(
                    {"setting": "Seller-reviewed contract", "value": contract_evidence}
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
            eligible = {
                r["sku"]
                for r in result["Campaign_Simulations"]
                if r["safe"] and r.get("decision_ready", True)
            }
            cols[3].metric("SKUs with confirmed-cost campaigns", len(eligible))
            st.columns([1, 2, 1])[1].download_button(
                "Download results workbook",
                st.session_state["download"],
                "marketprice_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                on_click="ignore",
                type="primary",
            )
            provisional = sum(
                r["cost_confidence"] != "CONFIRMED_INPUTS" for r in result.get("Cost_Confidence", [])
            )
            if provisional:
                st.warning(
                    f"{provisional} products have missing or estimated costs: their prices are provisional and cannot be approved."
                )
            st.subheader("Action list (اقدامات پیشنهادی)")
            st.dataframe(preview(result.get("Action_List", [])[:1000]), hide_index=True)
            st.caption(
                "Missing costs block actionable advice. Confirmed inputs still require checking your actual seller fee contract. Impacts are per unit and grouped by currency."
            )
            tabs = st.tabs(["Products", "Recommendations", "Campaigns", "Errors & warnings", "Audit"])
            for tab, sheet in zip(
                tabs[:3], ["Product_Calculations", "Price_Recommendations", "Campaign_Simulations"]
            ):
                with tab:
                    data = [
                        {k: display_value(k, v) for k, v in row.items() if not k.startswith("original_")}
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
                "Compare your selected margins: Increase / افزایش, Review decrease / بررسی کاهش, Keep / حفظ قیمت. A floor alone never justifies cutting a profitable price. A higher unit margin does not prove higher total profit; demand is not estimated."
            )
            st.dataframe(
                preview(result["Price_Analysis"][:1000]),
                hide_index=True,
            )
            st.subheader("Seasonal campaign offers (پیشنهاد کمپین مناسبتی)")
            st.caption(
                "SAFE describes mathematical feasibility only; check cost_confidence and decision_ready before acting. Required sales multiplier shows how many units would preserve baseline contribution, not a demand forecast. NO_SAFE_OFFER means no permitted discount meets them. Percentages shown here are rounded for display. Exact values and every product are in the export."
            )
            st.dataframe(
                preview(result["Seasonal_Campaigns"][:1000]),
                hide_index=True,
            )
            with st.expander("Review price changes (تأیید تغییر قیمت)"):
                candidates = {
                    (r["row"], str(r["target_margin"])): r
                    for r in result["Price_Analysis"]
                    if r.get("decision_ready")
                }
                approved = st.multiselect(
                    "Select one scenario per product",
                    list(candidates),
                    format_func=lambda k: (
                        f"{candidates[k]['sku']} · {candidates[k]['target_margin'] * 100}% · {candidates[k]['normal_price']} {candidates[k]['currency']}"
                    ),
                    key="approve_" + fingerprint,
                )
                fees_confirmed = st.checkbox(
                    "I checked these prices against my current seller fee contract", key="fee_" + fingerprint
                )
                if approved and fees_confirmed:
                    changes = approved_changes(
                        result, approved, expected_snapshot=snapshot(result), fee_rules_confirmed=True
                    )
                    st.download_button(
                        "Download approved change manifest",
                        json.dumps(changes, default=json_default, ensure_ascii=False, indent=2),
                        "marketprice_approved.json",
                    )
                    st.caption(
                        "Review manifest only; not an official marketplace upload template. No prices have been published."
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
