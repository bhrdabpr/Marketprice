"""Transaction workspace; imports are explicit normalized schemas, not vendor adapters."""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from .actuals import reconcile
from .io import read_upload, workbook_bytes


def render_operations():
    st.subheader("Actual profit and settlements (سود واقعی و تسویه)")
    st.caption(
        "Use normalized transaction and dated-cost exports. Vendor-native templates are not yet certified. Amounts must exclude collected VAT; expenses are negative. Payouts are transfers, not revenue."
    )
    samples = Path(__file__).resolve().parent.parent / "samples" / "operations"
    for filename in ("transactions.csv", "costs.csv"):
        st.download_button("Sample " + filename, (samples / filename).read_bytes(), filename, key=filename)
    transactions = st.file_uploader("Transactions (تراکنش ها)", type=["csv", "xlsx"], key="transactions")
    costs = st.file_uploader("Dated costs (هزینه های تاریخ دار)", type=["csv", "xlsx"], key="costs")
    as_of = st.date_input("Reporting date (تاریخ گزارش)", value=date.today())
    confirmed = st.checkbox(
        "I reviewed signs, currency, VAT treatment and completeness; cost events exclude purchase COGS"
    )
    current = (
        transactions.getvalue() if transactions else None,
        costs.getvalue() if costs else None,
        as_of,
        confirmed,
    )
    demo = st.button("Try synthetic demo (نمونه آزمایشی)")
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
        "Analyze actual profit (تحلیل سود واقعی)",
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
            st.error(str(exc))
    if current != st.session_state.get("operations_input"):
        st.session_state.pop("operations_result", None)
    saved_result = st.session_state.get("operations_result")
    if saved_result:
        result = saved_result
        if st.session_state.get("operations_demo"):
            st.info(
                "Synthetic demo — reporting date 2026-11-01. These are invented examples, not your business data."
            )
        st.warning(
            "These are results for the supplied extract. Missing periods or unreported charges cannot be detected automatically. Review unallocated costs before comparing individual products."
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
            st.subheader(sheet.replace("_", " "))
            st.dataframe(pd.DataFrame(result[sheet][:1000]).astype(str), hide_index=True)
        st.download_button(
            "Download reconciliation evidence", workbook_bytes(result), "marketprice_actuals.xlsx"
        )
