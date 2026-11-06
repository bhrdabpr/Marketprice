"""Transaction workspace; imports are explicit normalized schemas, not vendor adapters."""

from datetime import date
from pathlib import Path

import streamlit as st

from .actuals import reconcile
from .digikala import review_digikala_invoice
from .i18n import translate
from .io import read_upload, workbook_bytes
from .presentation import preview


def render_operations(language="en", display_currency="original", persian_digits=False):
    def t(text):
        return translate(text, language)

    st.subheader(t("Actual profit and settlements (سود واقعی و تسویه)"))
    st.caption(
        t(
            "Use normalized transaction and dated-cost exports. Vendor-native templates are not yet certified. Amounts must exclude collected VAT; expenses are negative. Payouts are transfers, not revenue."
        )
    )
    with st.expander(t("Digikala native invoice review"), expanded=False):
        st.caption(
            t(
                "Upload the original Digikala invoice XLSX. The review reconciles the payable amount, derives rates observed in this file, and keeps charges without order keys unallocated."
            )
        )
        st.info("نسبت هزینه به فروش فقط مشاهده همین فایل است. سقف ارسال و پردازش، دسته کالا و تاریخ اعتبار باید از قرارداد تعیین شوند؛ این گزارش قواعد قیمت‌گذاری را تغییر نمی‌دهد."
                if language == "fa" else "Ratios describe this file only. Shipping/processing caps, category and effective dates require contract evidence. This report does not change pricing rules.")
        digikala_file = st.file_uploader(
            t("Digikala invoice XLSX"),
            type=["xlsx"],
            key=f"digikala_invoice__session_{st.session_state.get('session_epoch', 0)}",
        )
        current_digikala = digikala_file.getvalue() if digikala_file else None
        if st.button(t("Review Digikala invoice"), disabled=digikala_file is None):
            assert digikala_file is not None
            try:
                st.session_state["digikala_invoice_result"] = review_digikala_invoice(
                    digikala_file.getvalue(), digikala_file.name
                )
                st.session_state["digikala_invoice_input"] = current_digikala
            except ValueError as exc:
                st.error(t(str(exc)))
        if current_digikala != st.session_state.get("digikala_invoice_input"):
            st.session_state.pop("digikala_invoice_result", None)
        digikala_result = st.session_state.get("digikala_invoice_result")
        if digikala_result:
            tax_check = digikala_result["Tax_Check"][0]
            if tax_check["label_mismatch"]:
                st.warning(t("The invoice VAT label and the amount calculation do not match. Review Tax Check."))
            for sheet in (
                "Invoice_Reconciliation",
                "Tax_Check",
                "Observed_Rules",
                "Order_Net_Before_Cost",
                "Unallocated_Charges",
                "Errors",
            ):
                st.subheader(t(sheet.replace("_", " ")))
                st.dataframe(
                    preview(
                        digikala_result[sheet],
                        language=language,
                        display_currency=display_currency,
                        persian_digits=persian_digits,
                    ),
                    hide_index=True,
                )
            st.download_button(
                t("Download Digikala invoice evidence"),
                workbook_bytes(digikala_result),
                "marketprice_digikala_invoice_review.xlsx",
                on_click="ignore",
            )
            st.download_button(
                t("Download normalized Digikala transactions"),
                workbook_bytes({"Transactions": digikala_result["Normalized_Transactions"]}),
                "marketprice_digikala_transactions.xlsx",
                on_click="ignore",
            )
    samples = Path(__file__).resolve().parent.parent / "samples" / "operations"
    for filename in ("transactions.csv", "costs.csv"):
        st.download_button(t("Sample " + filename), (samples / filename).read_bytes(), filename, key=filename, on_click="ignore")
    transactions = st.file_uploader(t("Transactions (تراکنش ها)"), type=["csv", "xlsx"], key=f"transactions__session_{st.session_state.get('session_epoch', 0)}")
    costs = st.file_uploader(t("Dated costs (هزینه های تاریخ دار)"), type=["csv", "xlsx"], key=f"costs__session_{st.session_state.get('session_epoch', 0)}")
    as_of = st.date_input(t("Reporting date (تاریخ گزارش)"), value=date.today(), key="operations_as_of")
    confirmed = st.checkbox(
        t("I reviewed signs, currency, VAT treatment and completeness; cost events exclude purchase COGS"),
        key="operations_confirmed",
    )
    current = (
        transactions.getvalue() if transactions else None,
        costs.getvalue() if costs else None,
        as_of,
        confirmed,
    )
    demo = st.button(t("Try synthetic demo (نمونه آزمایشی)"), key="operations_demo_button")
    if demo:
        st.session_state["operations_result"] = reconcile(
            read_upload(
                (samples / "transactions.csv").read_bytes(), "transactions.csv", preserve_headers=True
            ),
            read_upload((samples / "costs.csv").read_bytes(), "costs.csv", preserve_headers=True),
            as_of=date(2026, 11, 1),
        )
        st.session_state["operations_input"] = current
        st.session_state["operations_demo"] = True
    if st.columns([1, 2, 1])[1].button(
        t("Analyze actual profit (تحلیل سود واقعی)"),
        disabled=not (transactions and costs and confirmed),
        width="stretch",
    ):
        assert transactions is not None and costs is not None
        try:
            result = reconcile(
                read_upload(transactions.getvalue(), transactions.name, preserve_headers=True),
                read_upload(costs.getvalue(), costs.name, preserve_headers=True),
                as_of=as_of,
            )
            st.session_state["operations_result"] = result
            st.session_state["operations_input"] = current
            st.session_state["operations_demo"] = False
        except ValueError as exc:
            st.error(t(str(exc)))
    if current != st.session_state.get("operations_input"):
        st.session_state.pop("operations_result", None)
    saved_result = st.session_state.get("operations_result")
    if saved_result:
        result = saved_result
        if st.session_state.get("operations_demo"):
            st.info(
                t(
                    "Synthetic demo — reporting date 2026-11-01. These are invented examples, not your business data."
                )
            )
        st.warning(
            t(
                "These are results for the supplied extract. Missing periods or unreported charges cannot be detected automatically. Review unallocated costs before comparing individual products."
            )
        )
        for sheet in (
            "Action_List",
            "Platform_Comparison",
            "Product_Platform",
            "Order_Contribution",
            "Settlement_Reconciliation",
            "Campaign_Actuals",
            "Errors",
        ):
            st.subheader(t(sheet.replace("_", " ")))
            st.dataframe(
                preview(
                    result[sheet][:1000],
                    language=language,
                    display_currency=display_currency,
                    persian_digits=persian_digits,
                ),
                hide_index=True,
            )
        st.download_button(
            t("Download reconciliation evidence"), workbook_bytes(result), "marketprice_actuals.xlsx", on_click="ignore"
        )
