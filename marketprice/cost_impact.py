"""Incremental cost scenario; never a reconstruction of net business profit."""
from decimal import Decimal

from .precision import financial


@financial
def cost_impact(units, return_rate, reverse_cost, writeoff, storage, months, penalties):
    values = [Decimal(str(v)) for v in (units, return_rate, reverse_cost, writeoff, storage, months, penalties)]
    if any(not v.is_finite() or v < 0 for v in values):
        raise ValueError("Costs must be finite and nonnegative.")
    units, rate, reverse, loss, holding, duration, fines = values
    if units <= 0 or units != units.to_integral_value() or rate > 1:
        raise ValueError("Use positive integer units and a return rate between 0 and 1.")
    returns = units * rate
    return_cost = returns * (reverse + loss)
    storage_cost = holding * duration
    total = return_cost + storage_cost + fines
    return {"expected_returns": returns, "return_cost": return_cost, "storage_cost": storage_cost, "penalties": fines, "total": total, "per_unit": total / units}


def render_cost_impact(language):
    import json

    import streamlit as st
    fa = language == "fa"
    def t(en, persian):
        return persian if fa else en
    st.caption(t("Incremental scenario for one period. Use one currency and exclude costs already counted elsewhere.", "سناریوی هزینه اضافی یک دوره؛ همه مبالغ با یک واحد و بدون هزینه‌هایی که قبلاً محاسبه شده‌اند."))
    epoch = st.session_state.get("session_epoch", 0)
    currency = st.selectbox(t("Currency", "واحد پول"), ["IRR", "TOMAN", "USD", "EUR", "Other"], key=f"cost_impact_currency_{epoch}")
    a, b = st.columns(2)
    with a, st.container(border=True):
        st.subheader(t("Returns", "مرجوعی"))
        units = st.number_input(t("Units dispatched in the period", "تعداد ارسال در دوره"), min_value=1, value=100, key=f"cost_impact_units_{epoch}")
        rate = st.number_input(t("Expected return rate (%)", "نرخ مرجوعی مورد انتظار (%)"), min_value=0.0, max_value=100.0, value=0.0, key=f"cost_impact_rate_{epoch}")
        reverse = st.number_input(t("Reverse logistics per return", "هزینه برگشت و رسیدگی هر مرجوعی"), min_value=0.0, key=f"cost_impact_reverse_{epoch}")
        writeoff = st.number_input(t("Unrecoverable value per return", "افت ارزش غیرقابل بازیافت هر مرجوعی"), min_value=0.0, key=f"cost_impact_writeoff_{epoch}")
    with b, st.container(border=True):
        st.subheader(t("Holding & penalties", "ماندگاری و جریمه"))
        storage = st.number_input(t("Total monthly storage cost for this stock", "کل هزینه ماهانه نگهداری این موجودی"), min_value=0.0, key=f"cost_impact_storage_{epoch}")
        months = st.number_input(t("Storage duration (months)", "مدت نگهداری (ماه)"), min_value=0.0, value=1.0, key=f"cost_impact_months_{epoch}")
        penalties = st.number_input(t("Total penalties in the period", "کل جریمه‌های دوره"), min_value=0.0, key=f"cost_impact_penalties_{epoch}")
    result = cost_impact(units, Decimal(str(rate)) / 100, reverse, writeoff, storage, months, penalties)
    c, d, e = st.columns(3)
    c.metric(t("Additional cost", "هزینه اضافی"), f'{result["total"]:,.2f} {currency}')
    d.metric(t("Cost per dispatched unit", "هزینه هر واحد ارسال‌شده"), f'{result["per_unit"]:,.2f} {currency}')
    e.metric(t("Expected returns", "تعداد مرجوعی مورد انتظار"), f'{result["expected_returns"]:,.2f}')
    with st.expander(t("Calculation details", "جزئیات محاسبه")):
        st.write(t("Returns × (reverse logistics + unrecoverable value) + monthly storage × months + penalties. This excludes lost revenue, tax refunds and capital cost; it is not net profit.", "تعداد مرجوعی × (هزینه برگشت + افت ارزش) + هزینه ماهانه نگهداری × ماه + جریمه. درآمد از دست‌رفته، برگشت مالیات و هزینه سرمایه در این سناریو نیست؛ این عدد سود خالص نیست."))
    st.download_button(t("Download scenario", "دریافت سناریو"), json.dumps({"currency": currency, "inputs": {"units": units, "return_rate_percent": rate, "reverse_cost": reverse, "writeoff": writeoff, "monthly_storage": storage, "months": months, "penalties": penalties}, "results": result}, default=str, ensure_ascii=False, indent=2), "cost_scenario.json", on_click="ignore")
