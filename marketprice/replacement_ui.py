"""Bilingual offline replacement-cost and single-product campaign review."""

import hashlib
import json
from datetime import UTC, date, datetime

import streamlit as st

from .approvals import snapshot
from .i18n import translate
from .io import json_default, read_upload
from .presentation import preview
from .replacement import campaign_requirement, quote_template, review_replacement
from .validation import number


def render_replacement(result, *, language="en", display_currency="original", persian_digits=False):
    def t(text):
        return translate(text, language)

    def table(rows):
        st.dataframe(
            preview(
                rows[:1000],
                language=language,
                display_currency=display_currency,
                persian_digits=persian_digits,
            ),
            hide_index=True,
        )

    stamp = snapshot(result)
    suffix = stamp[:12]
    with st.expander(t("Replenishment and campaign budget")):
        st.caption(
            t(
                "Use a dated supplier quote to compare profit after buying the next unit. Quotes use net acquisition cost after recoverable purchase tax; other costs stay unchanged. No market price or demand is guessed."
            )
        )
        st.download_button(
            t("Download replacement quote template"),
            quote_template(result),
            "marketprice_replacement_quotes.csv",
            mime="text/csv",
            on_click="ignore",
        )
        quote_file = st.file_uploader(
            t("Completed replacement quotes (.csv)"),
            type=["csv"],
            key=f"replacement_quotes_{suffix}__session_{st.session_state.get('session_epoch', 0)}",
        )
        as_of = st.date_input(t("Quote review date"), value=date.today(), key="replacement_as_of")
        st.caption(
            t(
                "Keep the template identity and snapshot columns. Enter cost, quote date, expiry date and source reference. Dates use YYYY-MM-DD; amounts use each row's currency. No currency conversion."
            )
        )
        quote_suffix = suffix + "_" + as_of.isoformat()
        if quote_file is not None:
            quote_suffix += "_" + hashlib.sha256(quote_file.getvalue()).hexdigest()[:12]
        confirmed = st.checkbox(
            t("I checked quote dates, currency and net acquisition cost"),
            key="replacement_confirm_" + quote_suffix,
        )
        if quote_file is None or not confirmed:
            return
        try:
            quotes = read_upload(quote_file.getvalue(), quote_file.name, preserve_headers=True)
            reviewed = review_replacement(result, quotes, as_of=as_of)
            table(reviewed["Replacement_Review"])
            if reviewed["Quote_Errors"]:
                st.warning(t("Some quotes were rejected. Correct them before using the affected scenarios."))
                st.dataframe(reviewed["Quote_Errors"], hide_index=True)
            st.caption(
                t(
                    "Sensitivity only. Positive contribution is not target-margin compliance. All rows remain unapproved; missing costs and unsupported fee rules still need review."
                )
            )
            evidence = {
                "reviewed_at": datetime.now(UTC).isoformat(),
                "source_snapshot": stamp,
                "quotes": quotes,
                "review": reviewed,
            }
            st.download_button(
                t("Download replacement decision evidence"),
                json.dumps(evidence, default=json_default, ensure_ascii=False, indent=2),
                "marketprice_replacement_review.json",
                mime="application/json",
                on_click="ignore",
            )
            candidates = [
                r
                for r in reviewed["Replacement_Review"]
                if r.get("scenario") == "CAMPAIGN"
                and r.get("replacement_contribution") is not None
                and r.get("source_cost_confidence") == "CONFIRMED_INPUTS"
            ]
            if not candidates:
                return
            st.subheader(t("Campaign volume requirement"))
            st.caption(
                t(
                    "For one product and one review period: compare historical current-sale contribution with campaign contribution at replacement cost. Enter additional campaign-wide spending only; do not repeat per-unit costs already included. Required sales are not a sales forecast."
                )
            )
            review_suffix = snapshot(reviewed)[:12]
            choice = st.selectbox(
                t("Campaign scenario to review"),
                range(len(candidates)),
                format_func=lambda i: (
                    f"{candidates[i]['sku']} · {candidates[i]['scenario_price']} {candidates[i]['currency']}"
                ),
                key="replacement_campaign_" + review_suffix,
            )
            budget_suffix = review_suffix + "_" + str(choice)
            units = st.number_input(
                t("Baseline units in the review period"),
                min_value=0,
                max_value=10**9,
                value=0,
                key="replacement_units_" + budget_suffix,
            )
            budget_text = st.text_input(
                t("Additional campaign spending (scenario currency)"),
                "0",
                key="replacement_budget_" + budget_suffix,
            )
            budget_confirmed = st.checkbox(
                t("This additional spend is not already in the per-unit calculation"),
                key="replacement_budget_confirm_" + budget_suffix,
            )
            if not units or not budget_confirmed:
                return
            selected = candidates[choice]
            original = next(r for r in result["Product_Calculations"] if r["row"] == selected["row"])
            if "%" in budget_text or "٪" in budget_text:
                raise ValueError("Budget must be an amount, not a percentage")
            plan = {
                "row": selected["row"],
                "sku": selected["sku"],
                "currency": selected["currency"],
                **campaign_requirement(
                    baseline_profit=number(original["profit"]),
                    scenario_profit=number(selected["replacement_contribution"]),
                    baseline_units=units,
                    extra_spend=number(budget_text),
                ),
            }
            table([plan])
            st.download_button(
                t("Download campaign budget evidence"),
                json.dumps(
                    {
                        **evidence,
                        "selected_scenario": selected,
                        "campaign_requirement": plan,
                        "limit": "Single product, same period. Historical baseline versus replacement-cost campaign. No demand, portfolio or approval claim.",
                    },
                    default=json_default,
                    ensure_ascii=False,
                    indent=2,
                ),
                "marketprice_campaign_budget.json",
                mime="application/json",
                on_click="ignore",
            )
        except ValueError:
            st.error(
                t("Review quote columns, dates, identities and numeric amounts. No new decision is approved.")
            )
