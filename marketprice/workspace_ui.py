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


def overview(language):
    fa = language == 'fa'
    st.subheader('ابزار مورد نیازتان را انتخاب کنید' if fa else 'Choose your next task')
    st.caption('هر ابزار شما را از اطلاعات اولیه تا گزارش قابل دریافت راهنمایی می‌کند.' if fa else
               'Each tool takes you from your inputs to a report you can use.')
    cards = [
        ('Pricing (قیمت گذاری)', 'pricing', 'Price a product', 'قیمت‌گذاری محصول',
         'Bring purchase costs, fees and a margin target. Get price floors and margin scenarios.',
         'هزینه خرید، کارمزد و حاشیه سود هدف را وارد کنید؛ کف قیمت و سناریوهای سود را بگیرید.', 'Price report', 'گزارش قیمت'),
        ('Campaigns', 'campaigns', 'Check a campaign', 'بررسی کمپین',
         'Bring costs and current prices. Compare discounts, contribution and required sales volume.',
         'هزینه و قیمت فعلی را وارد کنید؛ تخفیف، سود و تعداد فروش لازم را مقایسه کنید.', 'Campaign evidence', 'گزارش کمپین'),
        ('Listings', 'listings', 'Review a listing', 'بررسی محتوای محصول',
         'Bring titles, bullets, descriptions and reference facts. Find inconsistencies and keyword review items.',
         'عنوان، ویژگی‌ها، توضیحات و مشخصات مرجع را وارد کنید؛ مغایرت و کلیدواژه نیازمند بررسی را ببینید.', 'Content review · preview', 'بررسی محتوا · نسخه اولیه'),
        ('Actual profit (سود واقعی)', 'actuals', 'Review actual profit', 'بررسی سود واقعی',
         'Reconcile transaction and cost reports against your settlements.',
         'گزارش تراکنش و هزینه را با تسویه تطبیق دهید.', 'Reconciliation workbook', 'گزارش تطبیق'),
        ('Cost impact', 'costs', 'Understand hidden costs', 'شناخت هزینه‌های پنهان',
         'Estimate the effect of returns, storage and penalties per dispatched unit.',
         'اثر مرجوعی، انبارداری و جریمه را برای هر واحد ارسالی برآورد کنید.', 'Cost breakdown', 'جزئیات هزینه'),
        ('Sales map', 'sales', 'Explore price & sales', 'بررسی قیمت و فروش',
         'Compare observed sales velocity within a comparable product group.',
         'سرعت فروش ثبت‌شده را در گروه محصولات مشابه مقایسه کنید.', 'Descriptive analysis', 'تحلیل توصیفی'),
        ('Changes', 'changes', 'Compare two reviews', 'مقایسه دو بررسی',
         'Bring earlier and latest MarketPrice workbooks. Trace per-unit changes.',
         'دو گزارش قدیمی و جدید MarketPrice را وارد کنید؛ تغییرات هر واحد را ببینید.', 'Change report', 'گزارش تغییرات'),
    ]
    for offset in range(0, len(cards), 3):
        for col, card in zip(st.columns(3), cards[offset:offset+3]):
            section, key, title, title_fa, description, description_fa, output, output_fa = card
            with col, st.container(border=True):
                st.caption(output_fa if fa else output)
                st.subheader(title_fa if fa else title)
                st.write(description_fa if fa else description)
                st.button('شروع ←' if fa else 'Start →', key='tool_'+key,
                          on_click=navigate, args=(section,), width='stretch')
    with st.expander('چه چیزهایی هنوز آماده نیست؟' if fa else 'What is still in development?'):
        st.write('پژوهش خودکار کلیدواژه و رقبا، نگارش هوشمند و انتشار مستقیم هنوز آماده نیست. ابزار محتوا بررسی واژگانی و عددی انجام می‌دهد.' if fa else
                 'Automated keyword and competitor research, AI copywriting and direct publishing are not available yet. Listing review currently checks wording and explicit quantities.')
    st.caption('فایل محرمانه دارید؟ برنامه را محلی اجرا کنید. نسخه وب فایل‌ها را روی سرور پردازش می‌کند.' if fa else
               'Working with confidential files? Run locally. The hosted app processes uploads on its server.')
