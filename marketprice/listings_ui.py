"""Session-local catalog review with explicit mapping and literal workbook export."""

import hashlib
import json

import streamlit as st

from .io import read_upload, workbook_bytes, workbook_sheets
from .listings import FIELDS, map_listing_rows, review_listings, suggest_listing_mapping
from .workspace_ui import steps

SAMPLE = b"""sku,title,highlights,bullet_1,description,keywords,product_type,brand,model,reference
BOTTLE-001,Acme Flow 1 L bottle,Best premium bottle,Stainless steel,Acme Flow stainless steel bottle,"steel bottle; gaming laptop; best",bottle,Acme,Flow,Acme Flow stainless steel water bottle capacity 500 ml
"""


def render_listings(language):
    def t(en, fa):
        return fa if language == "fa" else en

    steps(language)
    st.subheader(t("1 · Choose your market and file", "۱ · انتخاب بازار و فایل"))
    marketplace = st.selectbox(t("Target Amazon store", "بازار آمازون"), ["amazon.com", "amazon.ae"], key="listing_marketplace")
    st.caption(
        t(
            "Review listing text against your product specifications. No purchase costs required. "
            "Files stay in this server session; no external AI/API calls. Use local launch for confidential files.",
            "متن آگهی را با مشخصات مرجع کالا بررسی کنید؛ قیمت خرید لازم نیست. فایل در نشست همین سرور پردازش می‌شود "
            "و به هوش مصنوعی یا API خارجی ارسال نمی‌شود. برای فایل محرمانه برنامه را محلی اجرا کنید.",
        )
    )
    st.info(
        t(
            "This first version flags numeric conflicts, repeated content, vague wording and keywords needing evidence. "
            "It does not measure keyword popularity or reliably recognize synonyms. Detailed findings are in English.",
            "این نسخه مغایرت عددی، متن تکراری، عبارت مبهم و کلیدواژه نیازمند بررسی را مشخص می‌کند. "
            "محبوبیت کلیدواژه یا مترادف‌ها را تشخیص قطعی نمی‌دهد. جزئیات یافته‌ها انگلیسی است.",
        )
    )
    st.download_button(
        t("Download example catalog", "دریافت نمونه کاتالوگ"),
        SAMPLE,
        "listing_example.csv",
        on_click="ignore",
    )
    epoch = st.session_state.get("session_epoch", 0)
    upload = st.file_uploader(
        t("Listing catalog (.csv / .xlsx)", "کاتالوگ محتوا (.csv / .xlsx)"),
        type=["csv", "xlsx"],
        key=f"listing_upload_{epoch}",
        max_upload_size=50,
    )
    demo = st.checkbox(t("Try the synthetic example", "آزمایش نمونه ساختگی"), key=f"listing_demo_{epoch}")
    if upload is None and not demo:
        return
    data, filename = (upload.getvalue(), upload.name) if upload is not None else (SAMPLE, "example.csv")
    digest = hashlib.sha256(data).hexdigest()
    sheet, delimiter, encoding = None, ",", "utf-8-sig"
    try:
        if filename.lower().endswith(".xlsx"):
            sheet = st.selectbox(
                t("Listing worksheet", "برگه کاتالوگ"),
                workbook_sheets(data),
                key=f"listing_sheet_{digest}_{epoch}",
            )
        else:
            delimiter = st.selectbox(
                t("CSV separator", "جداکننده CSV"),
                [",", ";", "\t"],
                format_func=lambda x: {",": "Comma (,)", ";": "Semicolon (;)", "\t": "Tab"}[x],
                key=f"listing_separator_{epoch}",
            )
            encoding = st.selectbox(
                t("Listing encoding", "کدگذاری متن"),
                ["utf-8-sig", "utf-16", "cp1256", "cp1252"],
                key=f"listing_encoding_{epoch}",
            )
        rows = read_upload(
            data, filename, sheet_name=sheet, preserve_headers=True, delimiter=delimiter, encoding=encoding
        )
        st.subheader(t("2 · Check columns and reference facts", "۲ · بررسی ستون‌ها و مشخصات مرجع"))
        st.dataframe(rows[:10], hide_index=True)
        st.caption(
            t(
                "Map verified facts separately from listing copy. Keywords may be separated by commas, "
                "semicolons or newlines. Only mapped columns enter the report.",
                "مشخصات مرجع را جدا از متن آگهی تطبیق دهید. کلیدواژه‌ها با ویرگول، نقطه‌ویرگول یا خط جدید جدا شوند. "
                "فقط ستون‌های انتخاب‌شده وارد گزارش می‌شوند.",
            )
        )
        suggestions = suggest_listing_mapping(list(rows[0]))
        options = ["Ignore", *FIELDS]
        mapping = {}
        with st.expander(t("Column mapping", "تطبیق ستون‌ها"), expanded=True):
            for i, (column, target) in enumerate(suggestions.items()):
                mapping[column] = st.selectbox(
                    str(column),
                    options,
                    index=options.index(target),
                    key=f"listing_map_{digest}_{sheet}_{i}_{epoch}",
                )
        confirmed = st.checkbox(
            t(
                "Reference specifications come from a source I trust",
                "مشخصات مرجع از منبع مورد تأیید من آمده است",
            ),
            key=f"listing_reference_{digest}_{epoch}",
        )
        mapped = map_listing_rows(rows, mapping)
        # Full request fingerprint prevents stale reports after any input/mapping change.
        fingerprint = hashlib.sha256(
            json.dumps([digest, sheet, delimiter, encoding, mapping, confirmed, marketplace], sort_keys=True).encode()
        ).hexdigest()
        st.subheader(t("3 · Run the content checks", "۳ · اجرای بررسی محتوا"))
        if st.button(t("Review catalog listings", "بررسی محتوای کاتالوگ"), key="listing_run", type="primary"):
            result = review_listings(mapped, reference_confirmed=confirmed)
            result["Sources"] = [
                {
                    "marketplace": marketplace,
                    "policy_validation": "NOT_IMPLEMENTED",
                    "filename": filename,
                    "sha256": digest,
                    "sheet": sheet or "",
                    "mapping": json.dumps(mapping, ensure_ascii=False),
                }
            ]
            st.session_state["listing_result"] = (fingerprint, result)
        saved = st.session_state.get("listing_result")
        if saved and saved[0] == fingerprint:
            result = saved[1]
            st.subheader(t("4 · Review findings and download", "۴ · بررسی یافته‌ها و دریافت گزارش"))
            st.caption(t("The selected store is recorded for context. Store-specific policy certification and live keyword research are not yet available.", "بازار انتخاب‌شده در گزارش ثبت می‌شود؛ تأیید قواعد اختصاصی بازار و پژوهش زنده کلیدواژه هنوز آماده نیست."))
            columns = st.columns(3)
            columns[0].metric(t("Products", "محصولات"), len(result["Listing_Summary"]))
            columns[1].metric(t("Review items", "موارد بررسی"), len(result["Listing_Issues"]))
            columns[2].metric(t("Keywords checked", "کلیدواژه‌های بررسی‌شده"), len(result["Keyword_Review"]))
            st.dataframe(result["Listing_Summary"], hide_index=True)
            st.dataframe(result["Listing_Issues"], hide_index=True)
            if result["Keyword_Review"]:
                st.dataframe(result["Keyword_Review"], hide_index=True)
            st.download_button(
                t("Download listing review workbook", "دریافت گزارش اکسل محتوا"),
                workbook_bytes(result),
                "listing_review.xlsx",
                on_click="ignore",
            )
    except ValueError as exc:
        st.error(str(exc))
