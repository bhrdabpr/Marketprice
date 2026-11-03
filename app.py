"""Local-first UI. No uploaded data is cached globally or sent to external APIs."""

import hashlib
import json
from datetime import date

import pandas as pd
import streamlit as st

from marketprice.approvals import approved_changes, snapshot
from marketprice.batch import COST_FIELDS, process
from marketprice.channels import CHANNELS, channel_label, excluded_columns, matching_fields, scoped_mapping
from marketprice.config import load_profiles
from marketprice.contracts import load_contract
from marketprice.flexible import calculate_catalog
from marketprice.i18n import translate
from marketprice.importing import IGNORE, UNMAPPED, map_rows, suggest_mapping
from marketprice.io import json_default, read_upload, workbook_bytes
from marketprice.models import CURRENCIES, Product
from marketprice.operations_ui import render_operations
from marketprice.presentation import field_label, filter_results
from marketprice.presentation import preview as localized_preview
from marketprice.samples import sample_rows
from marketprice.templates import load_setup, save_setup
from marketprice.validation import number


def t(text):
    return translate(text, language)


def label(field):
    return field_label(field, language)


def preview(records):
    return localized_preview(
        records, language=language, display_currency=display_currency, persian_digits=persian_digits
    )


def select_localized(title, options, *, key, format_func=None, index=0, container=None, **kwargs):
    """Refresh translated selected labels while retaining canonical business choices."""
    options = list(options)
    widget_key = key + "__" + language
    previous = st.session_state.get(widget_key, st.session_state.get(key, options[index]))
    if previous not in options:
        if UNMAPPED in options and previous in Product.model_fields:
            options.append(previous)
        else:
            previous = options[index]
    value = (container or st).selectbox(
        title, options, index=options.index(previous), key=widget_key, format_func=format_func, **kwargs
    )
    st.session_state[key] = value
    return value


st.set_page_config(page_title="MarketPrice • pricing you can explain", page_icon="◈", layout="wide")
language = st.radio(
    "Language / زبان",
    ["en", "fa"],
    format_func=lambda value: "English" if value == "en" else "فارسی",
    horizontal=True,
    key="ui_language",
)
display_cols = st.columns(2)
display_currency = select_localized(
    t("Display currency"),
    ["original", "IRR", "TOMAN"],
    format_func=lambda value: (
        t("Original currency")
        if value == "original"
        else ({"IRR": "ریال", "TOMAN": "تومان"}[value] if language == "fa" else value)
    ),
    key="display_currency",
    container=display_cols[0],
)
persian_digits = display_cols[1].checkbox(
    t("Use Persian digits"), value=language == "fa", key="digits_" + language
)
st.caption(
    t(
        "Display units only; input units and exported amounts remain unchanged. 1 toman = 10 rial. Other currencies are never converted."
    )
)
direction = "rtl" if language == "fa" else "ltr"
st.markdown(
    f"<style>[data-testid='stMain'], [data-testid='stSidebar'] {{direction:{direction};text-align:{'right' if language == 'fa' else 'left'};font-family:Tahoma,'Segoe UI',Arial,sans-serif;}} h1,h2,h3,p,label,button,input {{font-family:Tahoma,'Segoe UI',Arial,sans-serif;}} [data-testid='stDataFrame'] {{direction:ltr;}} input {{text-align:{'right' if language == 'fa' else 'left'};}}</style>",
    unsafe_allow_html=True,
)
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
st.caption(t("Know your price floor. Test your campaign. Keep the calculation trail."))
st.info(
    t(
        "Example marketplace profiles • Enter your own verified fees and tax rules • All calculations run on this server"
    )
)
workspace = st.radio(
    t("Workspace (بخش برنامه)"),
    ["Pricing (قیمت گذاری)", "Actual profit (سود واقعی)"],
    horizontal=True,
    format_func=t,
    key="workspace",
)
if workspace == "Actual profit (سود واقعی)":
    render_operations(language, display_currency, persian_digits)
    st.stop()
profiles = load_profiles()
selected = select_localized(
    t("Choose a sales channel"),
    list(CHANNELS),
    format_func=lambda value: channel_label(value, language),
    key="sales_channel",
)
if selected == "custom":
    st.text_input(t("Your store name (optional)"), key="store_name")
with st.sidebar:
    st.header(t("Calculation settings"))
    flexible = st.checkbox(t("Flexible catalog (review cost confidence)"), value=True, key="flexible_mode")
    currency = select_localized(
        t("Currency for files without a currency column"),
        list(CURRENCIES),
        index=list(CURRENCIES).index("IRR"),
        format_func=lambda value: (
            {"IRR": "ریال (IRR)", "TOMAN": "تومان (TOMAN)"}.get(value, value) if language == "fa" else value
        ),
        key="input_currency",
    )
    target = st.text_input(t("Target margin for files without a target column"), "10%", key="target_margin")
    st.caption(
        t(
            "Flexible mode: absent costs/taxes produce provisional scenarios until confirmed inapplicable. Included columns need values for every product. Fixed tax amount → other_fixed; seller tax percentage → transaction_tax_rate. No current price → price floor only."
        )
    )
    locale = select_localized(t("Number format"), ["en", "fa", "comma"], format_func=t, key="input_locale")
    margins_text = st.text_input(
        t("Additional margin scenarios (semicolon separated)"), "15%; 25%", key="extra_margins"
    )
    discount_text = st.text_input(
        t("Campaign discounts (semicolon separated)"), "5%; 10%; 15%; 20%", key="campaign_discounts"
    )
    kind = select_localized(t("Discount type"), ["percent", "fixed"], format_func=t, key="discount_kind")
    share = st.text_input(t("Platform-funded share"), "0%", key="platform_share")
    override = st.checkbox(
        t("Explicitly allow unsafe campaign simulations (still labeled unsafe)"),
        value=False,
        key="allow_unsafe",
    )
    with st.expander(t("Seasonal offers (پیشنهادهای مناسبتی)")):
        event_names = st.multiselect(
            t("Events (مناسبت ها)"),
            ["Black Friday (جمعه سیاه)", "Christmas (کریسمس)", "Nowruz (نوروز)", "Yalda (یلدا)"],
            default=["Black Friday (جمعه سیاه)", "Nowruz (نوروز)"],
            format_func=t,
            key="event_selection",
        )
        events = []
        for event_name in event_names:
            event_margin = st.text_input(
                t(event_name + " — margin (حاشیه سود)"), "5%", key="event_margin_" + event_name
            )
            event_cost = st.text_input(
                t(event_name + " — extra cost per item (هزینه اضافی هر واحد)"),
                "0",
                key="event_cost_" + event_name,
            )
            events.append((event_name, event_margin, event_cost))
        st.caption(
            t(
                "Each event uses your own fees and margin. Identical settings produce identical offers. Suggestions use actual current prices, with no invented reference-price increases. Extra costs use each row's currency."
            )
        )
    st.caption(t("Analysis concerns unit prices and margins only (تحلیل قیمت و سود هر واحد)."))
st.columns([1, 2, 1])[1].download_button(
    t("Download sample input"),
    workbook_bytes({"Products": sample_rows()}),
    "sample_input.xlsx",
    on_click="ignore",
)
upload = st.file_uploader(
    t("Upload products (.xlsx or UTF-8 .csv)"), type=["xlsx", "csv"], key="catalog_upload"
)
st.caption(
    t(
        "25 MiB / 100,000 rows maximum. Required blanks cause errors; enter 0 only when confirmed. Samples include one intentional error."
    )
)
if upload is not None:
    try:
        raw_bytes = upload.getvalue()
        initial = read_upload(raw_bytes, upload.name, preserve_headers=True)
        source_market = selected
        if source_market:
            st.info(
                t(
                    "This file contains marketplace-specific columns. Only the selected marketplace's selling price, commission and shipping are used. Previous calculated prices and status columns are excluded; review the mapping below."
                )
            )
        setup_file = st.file_uploader(t("Reuse saved setup (.json)"), type=["json"], key="setup")
        setup = load_setup(setup_file.getvalue(), list(initial[0])) if setup_file else None
        if setup:
            saved = setup["settings"]
            currency = saved.get("currency", currency)
            target = saved.get("target_margin", target)
            saved_market = saved.get("marketplace", selected)
            if saved_market == "generic":
                saved_market = "custom"
            locale = saved.get("locale", locale)
            if source_market != saved_market:
                raise ValueError(
                    t("Saved setup belongs to another marketplace; select its sales channel above.")
                )
            st.info(
                t(
                    f"Saved settings active: {currency}, target {target}, marketplace {selected}, format {locale}. Remove setup to use sidebar settings."
                )
            )
        suggested = setup["mapping"] if setup else suggest_mapping(list(initial[0]), source_market)
        suggested = scoped_mapping(list(initial[0]), selected, suggested)
        suggested = {k: IGNORE if v == "quantity" else v for k, v in suggested.items()}
        excluded = excluded_columns(list(initial[0]), selected)
        if excluded:
            with st.expander(t("Automatically excluded columns")):
                st.write("، ".join(excluded))
        advanced_matching = st.checkbox(t("Advanced matching fields"), value=False)
        st.caption(t("Common product columns are shown first; advanced fields remain available."))
        setup_key = hashlib.sha256(setup_file.getvalue()).hexdigest()[:8] if setup_file else ""
        with st.expander(t("Column mapping"), expanded=True):
            st.caption(
                t(
                    "Review the suggested fields. Choose a field for unknown headers, or explicitly Ignore column. Amounts and percentage rates are different fields."
                )
            )
            mapping = {}
            conversions = {}
            for column in initial[0]:
                if column in excluded:
                    mapping[column] = IGNORE
                    continue
                choices = (
                    [UNMAPPED]
                    + matching_fields(selected, advanced=advanced_matching, suggested=suggested[column])
                    + [IGNORE]
                )
                samples = [str(row.get(column))[:80] for row in initial[:3]]
                st.caption(t("Examples: " + " | ".join(samples)))
                mapping[column] = select_localized(
                    column,
                    choices,
                    index=choices.index(suggested[column]),
                    format_func=lambda field: label(field) if field in Product.model_fields else t(field),
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
                    conversions[column] = select_localized(
                        t("Value format: " + column),
                        unit_options,
                        format_func=t,
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
                t("I reviewed the column meanings, ignored columns and units"),
                value=False,
                key="confirm_"
                + hashlib.sha256(
                    repr((raw_bytes[:128], mapping, conversions, source_market)).encode()
                ).hexdigest(),
            )
        pending = [k for k, v in mapping.items() if v == UNMAPPED]
        if pending:
            st.warning(t("Choose a field or Ignore column for: " + ", ".join(pending)))
            st.stop()
        mapped = map_rows(initial, mapping, conversions)
        if source_market:
            mapped = [{**row, "marketplace": source_market} for row in mapped]
        default_tax = st.text_input(
            t("Seller tax expense rate (only when no tax column exists)"),
            setup["settings"].get("seller_tax", "0%") if setup else "0%",
            key="tax_" + setup_key,
        )
        st.caption(
            t(
                "Seller expense as a percentage of selling price, separate from collected VAT. If no tax column exists, enter the rate here. Zero means no seller tax expense."
            )
        )
        if "transaction_tax_rate" not in mapped[0]:
            mapped = [{**row, "transaction_tax_rate": default_tax} for row in mapped]
        if "marketplace" not in mapped[0]:
            mapped = [{**row, "marketplace": selected} for row in mapped]
        omitted_confirmed = st.checkbox(
            t(
                "I confirm omitted cost categories are inapplicable or included elsewhere (zero additional cost)"
            ),
            value=setup["settings"].get("omitted_costs_confirmed", False) if setup else False,
            key="omitted_" + setup_key,
        )
        estimated_fields = st.multiselect(
            t("Which included costs are estimates? (هزینه های تخمینی)"),
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
                t("Save reusable setup (ذخیره تنظیمات)"),
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
            t("Optional dated seller rule bundle (.json)"), type=["json"], key="contract"
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
                t(
                    "Seller-reviewed rule bundle loaded; evidence is declared, not independently verified. Unsupported rule fields are rejected."
                )
            )
        scope_enabled = st.checkbox(
            t("Configure applicable costs for this workbook"),
            value=False,
            disabled=flexible,
            key="cost_scope_enabled",
        )
        applicable = (
            st.multiselect(
                t("Applicable cost fields (all present columns are still validated)"),
                sorted(COST_FIELDS),
                default=sorted(set(mapped[0]) & COST_FIELDS),
                format_func=label,
                key="applicable_cost_fields",
            )
            if scope_enabled and not flexible
            else None
        )
        if scope_enabled:
            st.caption(
                t(
                    "Unselected cost fields are treated as zero only when their columns are absent. Present blank cells still cause product-level errors. Tax settings and purchase cost remain required."
                )
            )
        st.subheader(t("Input preview"))
        st.caption(
            t(
                "Input preview uses the original input currency; display conversion applies to calculated results only."
            )
        )
        st.dataframe(
            preview([{**r, "currency": r.get("currency", currency)} for r in mapped[:30]]), hide_index=True
        )
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
            t("Validate and calculate"), type="primary", disabled=not confirmed_mapping, width="stretch"
        )
        if calculate_clicked:
            margins = tuple(number(x.strip(), locale) for x in margins_text.split(";") if x.strip())
            discounts = tuple(number(x.strip(), locale) for x in discount_text.split(";") if x.strip())
            bar = st.progress(0.0, text=t("Validating and calculating independent products"))
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
            with st.spinner(t("Preparing audited workbook…")):
                st.session_state["download"] = workbook_bytes(result)
            st.session_state["result"] = result
            st.session_state["fingerprint"] = fingerprint
            bar.progress(1.0, text=t("Complete — results ready"))
        if "result" in st.session_state:
            result = st.session_state["result"]
            cols = st.columns(4)
            for col, item in zip(cols, result["Summary"][:3]):
                col.metric(
                    t(item["metric"]),
                    str(item["value"]).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
                    if persian_digits
                    else item["value"],
                )
            eligible = {
                r["sku"]
                for r in result["Campaign_Simulations"]
                if r["safe"] and r.get("decision_ready", True)
            }
            cols[3].metric(
                t("SKUs with confirmed-cost campaigns"),
                str(len(eligible)).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
                if persian_digits
                else len(eligible),
            )
            st.columns([1, 2, 1])[1].download_button(
                t("Download results workbook"),
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
                    t(
                        f"{provisional} products have missing or estimated costs: their prices are provisional and cannot be approved."
                    )
                )
            filter_choice = st.pills(
                t("Product status"),
                ["all", "valid", "invalid"],
                default="all",
                selection_mode="single",
                format_func=lambda value: t(
                    {
                        "all": "All products",
                        "valid": "Only valid products",
                        "invalid": "Only invalid products",
                    }[value]
                ),
                key="product_filter",
            )
            visible_result = filter_results(result, filter_choice or "all")
            st.subheader(t("Action list (اقدامات پیشنهادی)"))
            actions = visible_result.get("Action_List", [])[:1000]
            if actions:
                st.dataframe(preview(actions), hide_index=True)
            else:
                st.success(t("No actions needed for the selected products."))
            st.caption(
                t(
                    "Missing costs block actionable advice. Confirmed inputs still require checking your actual seller fee contract. Impacts are per unit and grouped by currency."
                )
            )
            tabs = st.tabs(
                [t(x) for x in ["Products", "Recommendations", "Campaigns", "Errors & warnings", "Audit"]]
            )
            for tab, sheet in zip(
                tabs[:3], ["Product_Calculations", "Price_Recommendations", "Campaign_Simulations"]
            ):
                with tab:
                    records = visible_result[sheet][:1000]
                    if sheet == "Product_Calculations":
                        problems: dict[int, list[str]] = {}
                        for error in result["Errors"]:
                            problems.setdefault(error["row"], []).append(label(error["field"]))
                        records = [
                            {
                                **{
                                    k: row.get(k)
                                    for k in (
                                        "sku",
                                        "name",
                                        "status",
                                        "currency",
                                        "price",
                                        "break_even",
                                        "profit",
                                        "margin",
                                    )
                                },
                                "problem": "، ".join(dict.fromkeys(problems.get(row["row"], []))) or None,
                            }
                            for row in records
                        ]
                    st.dataframe(preview(records), hide_index=True)
                    st.caption(t("Preview limited to 1,000 records. Download includes every input row."))
            with tabs[0]:
                values = [
                    float(r["margin"])
                    for r in visible_result["Product_Calculations"]
                    if r.get("margin") is not None
                ]
                if values:
                    buckets = pd.cut(
                        pd.Series(values),
                        [-float("inf"), 0, 0.1, 0.2, 0.3, float("inf")],
                        labels=[
                            t("Loss"),
                            *(
                                ["۰–۱۰٪", "۱۰–۲۰٪", "۲۰–۳۰٪", "۳۰٪+"]
                                if persian_digits
                                else ["0–10%", "10–20%", "20–30%", "30%+"]
                            ),
                        ],
                    ).value_counts(sort=False)
                    st.bar_chart(buckets)
            with tabs[3]:
                st.dataframe(preview(visible_result["Errors"]), hide_index=True)
                st.dataframe(preview(visible_result["Warnings"]), hide_index=True)
            st.subheader(t("Price analysis (تحلیل قیمت)"))
            st.caption(
                t(
                    "Compare your selected margins: Increase / افزایش, Review decrease / بررسی کاهش, Keep / حفظ قیمت. A floor alone never justifies cutting a profitable price. A higher unit margin does not prove higher total profit; demand is not estimated."
                )
            )
            st.dataframe(
                preview(visible_result["Price_Analysis"][:1000]),
                hide_index=True,
            )
            st.subheader(t("Seasonal campaign offers (پیشنهاد کمپین مناسبتی)"))
            st.caption(
                t(
                    "SAFE describes mathematical feasibility only; check cost_confidence and decision_ready before acting. Required sales multiplier shows how many units would preserve baseline contribution, not a demand forecast. NO_SAFE_OFFER means no permitted discount meets them. Percentages shown here are rounded for display. Exact values and every product are in the export."
                )
            )
            st.dataframe(
                preview(visible_result["Seasonal_Campaigns"][:1000]),
                hide_index=True,
            )
            with st.expander(t("Review price changes (تأیید تغییر قیمت)")):
                candidates = {
                    (r["row"], str(r["target_margin"])): r
                    for r in result["Price_Analysis"]
                    if r.get("decision_ready")
                }
                approved = st.multiselect(
                    t("Select one scenario per product"),
                    list(candidates),
                    format_func=lambda k: (
                        f"{candidates[k]['sku']} · {candidates[k]['target_margin'] * 100}% · {candidates[k]['normal_price']} {candidates[k]['currency']}"
                    ),
                    key="approve_" + fingerprint,
                )
                fees_confirmed = st.checkbox(
                    t("I checked these prices against my current seller fee contract"),
                    key="fee_" + fingerprint,
                )
                if approved and fees_confirmed:
                    changes = approved_changes(
                        result, approved, expected_snapshot=snapshot(result), fee_rules_confirmed=True
                    )
                    st.download_button(
                        t("Download approved change manifest"),
                        json.dumps(changes, default=json_default, ensure_ascii=False, indent=2),
                        "marketprice_approved.json",
                    )
                    st.caption(
                        t(
                            "Review manifest only; not an official marketplace upload template. No prices have been published."
                        )
                    )
            with tabs[4]:
                st.json(result["Assumptions"])
                st.caption(
                    t(
                        "Exact inputs, versions, rules and row identities are included in the workbook. No cross-currency totals."
                    )
                )
    except ValueError as exc:
        st.error(t(str(exc)))
    except Exception:  # noqa: BLE001 - UI boundary must suppress sensitive internals
        st.error(
            t(
                "Processing failed safely. Check the input and configuration; no recommendation is available for this run."
            )
        )
        st.session_state.pop("result", None)
        st.session_state.pop("download", None)
else:
    st.subheader(t("From workbook to defensible prices"))
    a, b, c = st.columns(3)
    a.markdown(t("**1 · Validate**\n\nMap columns and catch unknown costs before pricing."))
    b.markdown(t("**2 · Calculate**\n\nSeparate contribution, collected tax, and seller expenses."))
    c.markdown(
        t("**3 · Decide**\n\nCompare margin targets and funded campaigns, then export the audit trail.")
    )
    st.markdown(
        t(
            "**Privacy:** uploads and results stay in server session memory. Reset the session to clear them. Local launch binds to localhost."
        )
    )
