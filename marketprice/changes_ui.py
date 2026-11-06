"""Compare two seller-held exports in the current session."""

import hashlib

import streamlit as st

from .changes import compare_snapshots
from .io import read_upload, workbook_bytes


def render_changes(language):
    def t(en, fa):
        return fa if language == 'fa' else en

    st.caption(t('Upload two complete MarketPrice reports, earlier first. Differences are per unit and grouped by currency. Keep the same product variants and accounting assumptions.',
                 'دو گزارش کامل MarketPrice را به ترتیب قدیمی و جدید وارد کنید. اختلاف‌ها برای هر واحد و با تفکیک ارز هستند. تنوع کالا و فرض‌های حسابداری باید یکسان باشند.'))
    epoch = st.session_state.get('session_epoch', 0)
    old = st.file_uploader(t('Earlier report', 'گزارش قبلی'), type=['xlsx'], key=f'changes_old_{epoch}')
    new = st.file_uploader(t('Latest report', 'گزارش جدید'), type=['xlsx'], key=f'changes_new_{epoch}')
    if not old or not new:
        return
    try:
        payloads = [old.getvalue(), new.getvalue()]
        rows = [read_upload(data, 'report.xlsx', sheet_name='Product_Calculations',
                            preserve_headers=True) for data in payloads]
        result = compare_snapshots(*rows)
        result['Sources'] = [
            {'snapshot': side, 'filename': file.name, 'sha256': hashlib.sha256(data).hexdigest()}
            for side, file, data in zip(('previous', 'current'), (old, new), payloads, strict=True)
        ]
        st.dataframe(result['Changes'], hide_index=True)
        if result['Match_Errors']:
            st.warning(t('Some identities could not be matched. Review the errors below.',
                         'برخی شناسه‌ها قابل تطبیق نیستند؛ خطاهای زیر را بررسی کنید.'))
            st.dataframe(result['Match_Errors'], hide_index=True)
        st.download_button(t('Download change review', 'دریافت گزارش تغییرات'),
                           workbook_bytes(result), 'marketprice_changes.xlsx', on_click='ignore')
    except ValueError as exc:
        st.error(str(exc))
