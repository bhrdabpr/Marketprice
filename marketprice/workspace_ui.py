"""Task-oriented workspace shell. Decorative charts contain no business results."""
from html import escape

import streamlit as st

SECTIONS = {
    "Overview": ("Overview", "نمای کلی"),
    "Pricing (قیمت گذاری)": ("Pricing & campaigns", "قیمت و کمپین"),
    "Actual profit (سود واقعی)": ("Financial performance", "عملکرد مالی"),
    "Cost impact": ("Hidden costs", "هزینه‌های پنهان"),
    "Sales map": ("Price & sales", "قیمت و فروش"),
    "Changes": ("What changed?", "چه چیزی تغییر کرد؟"),
}


def section_label(section, language):
    return SECTIONS[section][language == "fa"]


def hero(section, language):
    fa = language == "fa"
    title = section_label(section, language)
    subtitle = {
        "Changes": ("Compare two catalog reviews.", "دو بررسی کاتالوگ را مقایسه کنید."),
        "Overview": ("Your next decision starts here.", "تصمیم بعدی شما از اینجا شروع می‌شود."),
        "Pricing (قیمت گذاری)": ("Turn costs into a price you can explain.", "از هزینه‌ها به یک قیمت قابل دفاع برسید."),
        "Actual profit (سود واقعی)": ("Follow your sales through to contribution and settlement.", "مسیر فروش تا سود عملیاتی و تسویه را دنبال کنید."),
        "Cost impact": ("See what returns, storage and penalties cost.", "اثر مرجوعی، ماندگاری و جریمه را ببینید."),
        "Sales map": ("Find the patterns behind your product mix.", "الگوی قیمت و فروش کالاهایتان را ببینید."),
    }[section][fa]
    badge = "فضای تحلیل فروشنده" if fa else "SELLER ANALYTICS"
    st.markdown(f'<div class="mp-hero"><div class="mp-hero-copy"><span class="mp-eyebrow">{badge}</span><h2>{escape(title)}</h2><p>{escape(subtitle)}</p><span class="mp-pill">Excel · CSV</span><span class="mp-pill">{"همه کانال‌های فروش" if fa else "Every sales channel"}</span></div><div class="mp-orbit" aria-hidden="true"><i></i><i></i><i></i><b>↗</b></div></div>', unsafe_allow_html=True)


def navigate(section):
    st.session_state["workspace"] = section


def overview(language):
    fa = language == "fa"
    st.subheader("از کجا شروع کنیم؟" if fa else "Choose your next move")
    cards = [
        ("Pricing (قیمت گذاری)", "01", "فایل هزینه‌ها، حاشیه‌های سود و سناریوهای تخفیف", "Costs, margin targets and discount scenarios"),
        ("Actual profit (سود واقعی)", "02", "فروش ثبت‌شده، هزینه‌ها و اختلاف تسویه", "Recorded sales, expenses and settlement differences"),
        ("Cost impact", "03", "مرجوعی، افت ارزش کالا، انبارداری و جریمه", "Returns, write-offs, storage and penalties"),
        ("Sales map", "04", "جایگاه قیمت، سرعت فروش و روند رشد", "Price position, sales velocity and growth"),
    ]
    columns = st.columns(2)
    for i, (key, number, persian, english) in enumerate(cards):
        with columns[i % 2], st.container(border=True):
            st.markdown(f'<span class="mp-card-number">{number}</span>', unsafe_allow_html=True)
            st.subheader(section_label(key, language))
            st.write(persian if fa else english)
            st.button("شروع بررسی ←" if fa else "Open workspace →", key="open_" + str(i), on_click=navigate, args=(key,), width="stretch")
    with st.expander("نقشه مسیر و قابلیت‌های آینده" if fa else "Workflow & upcoming capabilities"):
        st.write("فایل ← تطبیق ستون‌ها ← بررسی کیفیت ← تحلیل ← مقایسه سناریو ← گزارش" if fa else "File → Map columns → Validate → Analyze → Compare → Export")
        st.caption("بررسی پیشنهادهای رقبا در بخش کمپین موجود است. نمودار فروش دارای رگرسیون توصیفی است. جمع‌آوری خودکار بازار و تخمین اثر تغییر قیمت هنوز پیاده‌سازی نشده‌اند." if fa else "Seller-supplied competitor evidence is available in campaigns; the sales map includes descriptive regression. Automated market collection and causal price-response estimation are not implemented yet.")

