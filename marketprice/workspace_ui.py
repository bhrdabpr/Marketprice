"""Task chooser and shared guidance for the seller's workflows."""
from html import escape

import streamlit as st

SECTIONS = {
    "Overview": ("Home · choose a tool", "خانه · انتخاب ابزار"),
    "Pricing (قیمت گذاری)": ("Pricing & campaigns", "قیمت و کمپین"),
    "Campaigns": ("Campaign analysis", "تحلیل کمپین"),
    "Listings": ("Catalog listing review", "بررسی محتوای کاتالوگ"),
    "Actual profit (سود واقعی)": ("Financial performance", "عملکرد مالی"),
    "Cost impact": ("Hidden costs", "هزینه‌های پنهان"),
    "Sales map": ("Price & sales", "قیمت و فروش"),
    "Changes": ("What changed?", "چه چیزی تغییر کرد؟"),
}


def section_label(section, language):
    return SECTIONS[section][language == 'fa']


def navigate(section):
    st.session_state['workspace'] = section


def steps(language, labels=None):
    labels = labels or [('Upload your file', 'ورود فایل'), ('Check inputs', 'بررسی اطلاعات'),
                        ('Analyze & review', 'تحلیل و بررسی'), ('Download report', 'دریافت گزارش')]
    html = ''.join(f'<span><b>{i:02}</b> {escape(pair[language == "fa"])}</span>'
                   for i, pair in enumerate(labels, 1))
    st.markdown('<nav class="mp-steps" aria-label="Workflow steps">' + html + '</nav>',
                unsafe_allow_html=True)


def hero(section, language):
    fa = language == 'fa'
    title = 'MarketPrice' if section == 'Overview' else section_label(section, language)
    subtitle = {
        'Overview': ('What would you like to work on today?', 'امروز کدام بخش کسب‌وکارتان را بررسی می‌کنید؟'),
        'Pricing (قیمت گذاری)': ('Find a price that covers your costs and margin.', 'قیمتی پیدا کنید که هزینه و حاشیه سود شما را پوشش دهد.'),
        'Campaigns': ('Check a discount before you commit to it.', 'پیش از اجرای تخفیف، اثر آن بر سود را بررسی کنید.'),
        'Listings': ('Find mismatches and improve the clarity of your catalog.', 'مغایرت‌ها و عبارت‌های مبهم کاتالوگ را پیدا کنید.'),
        'Actual profit (سود واقعی)': ('Reconcile sales, expenses and settlements.', 'فروش، هزینه‌ها و تسویه را تطبیق دهید.'),
        'Cost impact': ('Understand the cost of returns, storage and losses.', 'هزینه مرجوعی، انبارداری و زیان را ببینید.'),
        'Sales map': ('Explore observed price and sales patterns.', 'الگوهای ثبت‌شده قیمت و فروش را بررسی کنید.'),
        'Changes': ('Compare an earlier report with your latest review.', 'گزارش قبلی و آخرین بررسی را مقایسه کنید.'),
    }[section][fa]
    st.markdown(f'<div class="mp-hero"><div class="mp-hero-copy"><span class="mp-eyebrow">MARKETPRICE · SELLER WORKSPACE</span>'
                f'<h2>{escape(title)}</h2><p>{escape(subtitle)}</p>'
                '<span class="mp-pill">Excel · CSV</span>'
                f'<span class="mp-pill">{"گزارش قابل بررسی" if fa else "Evidence you can review"}</span></div></div>',
                unsafe_allow_html=True)
    if section != 'Overview':
        st.button('← همه ابزارها' if fa else '← All tools', key='back_to_tools',
                  on_click=navigate, args=('Overview',))

