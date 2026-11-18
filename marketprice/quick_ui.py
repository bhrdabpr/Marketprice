"""The first-visit dashboard and automatic file reviews."""

import hashlib
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from .io import workbook_bytes, workbook_sheets
from .listing_urls import MAX_LINKS, read_products
from .quick_review import analyze, file_rows
from .seller_project import (
    changes,
    encode,
    export_project,
    next_revision,
    restore_project,
    revision,
    sign_in,
    team_history,
)
from .workspace_ui import SECTIONS, navigate, section_label

SERVICES = {
    "pricing": ("Price my products", "قیمت‌گذاری محصولات", "sell"),
    "campaign": ("Check my campaign", "بررسی تبلیغات", "ads_click"),
    "listing": ("Improve my listing", "بهبود محتوای محصول", "edit_note"),
    "profit": ("Check my profit", "بررسی سود", "payments"),
    "storage": ("Calculate storage cost", "محاسبه هزینه انبار", "warehouse"),
}
DETAILS = {
    "pricing": ("Add purchase cost and currency. Include fees and a target margin if you have them.",
                "هزینه خرید و ارز را بدهید. در صورت امکان کارمزد و حاشیه سود هدف را هم اضافه کنید."),
    "profit": ("Add purchase cost and selling price. For ROI, include net profit and invested capital for the same period and currency.",
               "هزینه خرید و قیمت فروش را بدهید. برای بازده سرمایه، سود خالص و سرمایه همان دوره و ارز را وارد کنید."),
    "campaign": ("Use one reporting period per row. Include impressions, clicks, spend, attributed orders, attributed sales and currency where available.",
                 "برای هر ردیف یک دوره انتخاب کنید. نمایش، کلیک، هزینه، فروش و سفارش منتسب و ارز را وارد کنید."),
    "storage": ("Include units stored, monthly storage fee per unit, months stored and currency. Split periods when stock or rates change.",
                "تعداد، هزینه ماهانه هر واحد، مدت به ماه و ارز را وارد کنید. دوره‌هایی با موجودی یا نرخ متفاوت را جدا کنید."),
    "listing": ("Use SKU or ASIN and title. Include bullet points, description and keywords if available.",
                "شناسه و عنوان را بدهید. ویژگی‌ها، توضیحات و کلیدواژه‌های موجود را هم اضافه کنید."),
}


def enter(task):
    st.session_state.pop("quick_reuse", None)
    st.session_state["quick_task"] = task


def sign_out():
    st.session_state.clear()


def team_access(language):
    try:
        config = st.secrets.get("team_project")
    except StreamlitSecretNotFoundError:
        config = None
    if config is None:
        return None, "", "manager"
    fa = language == "fa"
    user = st.session_state.get("team_user", "")
    proof = st.session_state.get("team_proof", "")
    members = config.get("members", {})
    member = members.get(user, {})
    if not proof or proof != member.get("token_sha256") or member.get("role") not in {"viewer", "editor", "manager"}:
        st.title("ورود به پروژه" if fa else "Open your team project")
        with st.form("team_login"):
            name = st.text_input("نام کاربری" if fa else "Member name")
            token = st.text_input("کلید دسترسی" if fa else "Access key", type="password")
            if st.form_submit_button("ورود" if fa else "Sign in"):
                try:
                    sign_in(members, name, token)
                    st.session_state.update(team_user=name, team_proof=hashlib.sha256(token.encode()).hexdigest())
                    st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
        st.stop()
    st.sidebar.button("خروج" if fa else "Sign out", on_click=sign_out)
    return config["database"], user, member["role"]


def source_links(text):
    lines = [v.strip() for v in text.splitlines() if v.strip()]
    if not 1 <= len(lines) <= MAX_LINKS:
        raise ValueError("Enter 1 to 20 Amazon product links.")
    groups: dict[str, list[str]] = {}
    for line in lines:
        host = (urlsplit(line).hostname or "").lower().removeprefix("www.")
        if host not in {"amazon.ae", "amazon.com"}:
            raise ValueError("Use full Amazon.com or Amazon.ae product links.")
        groups.setdefault(host, []).append(line)
    rows, sources = [], []
    for host, links in groups.items():
        parsed, observed = read_products(links, host)
        rows.extend(parsed)
        sources.extend(observed)
    return rows, sources


def up_to_date_review(rev):
    old_message = {"Next input": "Add purchase_cost and currency columns for per-unit prices and contribution."}
    if rev["task"] in {"pricing", "profit"} and old_message in rev["report"].get("Checks", []):
        return {**rev, "report": analyze(rev["task"], rev["inputs"])}
    return rev


def review_workbook(rev):
    report = rev["report"]
    tables = {"Summary": [{"Source": rev["source"], "Service": rev["task"], "Source rows": len(rev["inputs"]),
                           "Saved at": rev["time"], "Answer rows": len(report.get("Answers", report.get("Listing_Summary", [])))}]}
    for title in ("Checks", "Detected inputs", "Answers", "Cells to check", "Listing_Summary", "Listing_Issues",
                  "Keyword_Review", "Claim_Checks", "Check_Coverage", "Method", "Sources", "Cost details"):
        if report.get(title):
            tables[title] = report[title]
    tables["Source rows"] = rev["inputs"]
    return workbook_bytes(tables)


def continue_pricing(rev):
    st.session_state["pricing_source"] = ("project-inputs.xlsx", workbook_bytes({"Products": rev["inputs"]}))
    st.session_state["catalog_handoff"] = st.session_state.get("catalog_handoff", 0) + 1
    for key in ("result", "fingerprint", "download", "summary_download"):
        st.session_state.pop(key, None)
    navigate("Pricing (قیمت گذاری)")


def show_review(rev, fa, role):
    report = rev["report"]
    if rev["task"] == "listing":
        issues = report.get("Listing_Issues", [])
        st.subheader("موارد نیازمند بررسی" if fa else "What to check in your listing")
        if issues:
            first = next((i for i in issues if i.get("severity") == "ERROR"), issues[0])
            st.write(first.get("suggestion", ""))
            st.dataframe([{k: r.get(k) for k in ("sku", "field", "observed", "suggestion")} for r in issues],
                         hide_index=True)
        st.caption("این بررسی تقاضای جستجو و رتبه فروش را اندازه نمی‌گیرد." if fa else
                   "This review checks listing text. Search demand and sales rank require separate evidence.")
    else:
        needs_setup = "Detected inputs" in report
        if needs_setup:
            st.subheader("بررسی فایل قیمت‌گذاری" if fa else "Pricing setup needed")
            st.write(f"{len(rev['inputs']):,} ردیف خوانده شد." if fa else f"Read {len(rev['inputs']):,} source rows.")
        else:
            st.subheader("پاسخ شما" if fa else "Your answer")
        if rev["task"] in {"pricing", "profit"} and not needs_setup:
            st.caption("قیمت و سود هر واحد با هزینه‌های داده‌شده محاسبه شده‌اند. هدف پیش‌فرض سربه‌سر است." if fa else
                       "Price floors and unit contribution use the costs supplied. The default target is break-even. Confirm omitted fees and taxes before changing a price.")
        answers = report.get("Answers", [])
        if answers:
            primary = answers[0]
            labels = {"margin_floor": "Price floor", "cost_confidence": "Cost review", "profit": "Unit contribution",
                      "current_price": "Current price", "sku": "SKU", "currency": "Currency", "target_margin": "Target margin (fraction)"}
            if len(answers) == 1:
                preferred = {"campaign": ("CTR (%)", "Cost per attributed order", "ROAS (×)"),
                             "profit": ("Gross margin (%)", "Markup on purchase cost (%)", "ROI (%)"),
                             "pricing": ("margin_floor",), "storage": ("Storage cost",)}
                fields = [k for k in preferred[rev["task"]] if primary.get(k) is not None]
                for col, k in zip(st.columns(len(fields) or 1), fields):
                    unit = primary.get("Currency", primary.get("currency", "")) if k in {"Cost per attributed order", "margin_floor", "Storage cost"} else ""
                    col.metric(labels.get(k, k), f"{primary[k]} {unit}".strip())
            st.dataframe([{labels.get(k, k): v for k, v in r.items()} for r in answers], hide_index=True)
            if primary.get("Next input"):
                st.info(("اطلاعات تکمیلی: " if fa else "To complete the first row, add ") + primary["Next input"])
        for issue in report.get("Checks", [])[:4]:
            st.warning(str(issue.get("Next input") or issue.get("explanation") or issue))
        if needs_setup and role != "viewer":
            st.button("انتخاب بازار و واحدها" if fa else "Choose channel and units", type="primary",
                      on_click=continue_pricing, args=(rev,), key="continue_review_pricing")
        if report.get("Detected inputs"):
            st.table(report["Detected inputs"])
    if role != "viewer":
        st.download_button("دریافت گزارش اکسل" if fa else "Download review as Excel", lambda: review_workbook(rev),
                           "marketprice-review.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           on_click="ignore")
    details = st.expander("جزئیات و منبع" if fa else "See inputs and calculation details",
                          key="quick_details_"+rev["fingerprint"], on_change="rerun")
    if details.open:
        with details:
            for title, records in report.items():
                if records and title not in {"Answers", "Original_Listings", "Checks", "Detected inputs"}:
                    st.text(title)
                    if title == "Columns outside price calculation":
                        st.text(" · ".join(str(r.get("Column", "")) for r in records))
                    else:
                        st.dataframe(records[:100], hide_index=True)
            st.caption(("پیش‌نمایش ۱۰۰ ردیف اول" if fa else "Preview of the first 100 rows") + " · " + rev["source"])
            st.dataframe(rev["inputs"][:100], hide_index=True)


def dashboard(history, shared, role, fa):
    if history:
        latest = {r["task"]: r for r in history}
        overview = []
        for service, review in latest.items():
            report = up_to_date_review(review)["report"]
            next_input = ""
            for row in report.get("Answers", []):
                next_input = row.get("Check") or row.get("Next input") or row.get("For ROI")
                if next_input:
                    break
            if not next_input and report.get("Checks"):
                check = report["Checks"][0]
                next_input = check.get("Next input") or check.get("explanation")
            if not next_input and report.get("Listing_Issues"):
                issues = report["Listing_Issues"]
                next_input = next((i for i in issues if i.get("severity") == "ERROR"), issues[0]).get("suggestion")
            if not next_input and any(r.get("missing_costs") for r in report.get("Cost details", [])):
                next_input = "Confirm omitted fees and taxes."
            overview.append({("ابزار" if fa else "Service"): SERVICES[service][fa],
                             ("ردیف‌ها" if fa else "Rows in latest input"): len(review["inputs"]),
                             ("گام بعد" if fa else "What to do next"): next_input or ("مشاهده نتیجه" if fa else "Review the result.")})
        st.dataframe(overview, hide_index=True)
        n = st.selectbox("گزارش ذخیره‌شده" if fa else "Saved reviews", range(len(history)-1, -1, -1),
                         format_func=lambda i: f"{i+1} · {history[i]['source']} · {history[i]['time']}")
        rev = up_to_date_review(history[n])
        if rev.get("author"):
            st.caption(("ثبت توسط " if fa else "Saved by ") + rev["author"])
        show_review(rev, fa, role)
        earlier = [r for r in history[:n] if r["task"] == rev["task"]]
        if earlier:
            comparison = st.expander("تغییرات محصولات" if fa else "Compare with the previous input for this service",
                                     key="quick_compare", on_change="rerun")
            if comparison.open:
                with comparison:
                    delta = changes(earlier[-1]["inputs"], rev["inputs"])
                    if delta:
                        st.dataframe(delta, hide_index=True)
                    else:
                        st.write("تغییری دیده نشد." if fa else "The product rows match.")
        if role == "manager":
            st.caption("فایل JSON برای بازگشایی پروژه است." if fa else "The JSON backup reopens your project with its history.")
            st.download_button("دریافت کل پروژه" if fa else "Download whole project", lambda: export_project(history),
                               "marketprice-project.json", "application/json", on_click="ignore")
    else:
        st.info("اولین گزارش شما اینجا ذخیره می‌شود." if fa else "Your first review will appear here.")
    if not shared:
        saved = st.file_uploader("باز کردن پروژه ذخیره‌شده" if fa else "Open a saved project", type=["json"],
                                 key="project_restore", max_upload_size=32)
        if saved is not None:
            data = saved.getvalue()
            key = hashlib.sha256(data).hexdigest()
            if st.session_state.get("opened_project") != key:
                restored = restore_project(data)
                if history:
                    st.caption("ابتدا از پروژه فعلی نسخه بگیرید." if fa else
                               "Download your current project before switching.")
                if not history or st.button("تعویض پروژه" if fa else "Switch to this project"):
                    st.session_state.update(quick_history=restored, opened_project=key)
                    st.session_state.pop("quick_last", None)
                    st.rerun()


def render_quick(language, team):
    fa = language == "fa"
    path, user, role = team
    task = st.session_state.get("quick_task", "home") if role != "viewer" else "dashboard"
    history = team_history(path, role) if path else st.session_state.get("quick_history", [])
    st.sidebar.markdown("**راهنما**" if fa else "**Quick guide**")
    st.sidebar.markdown("1. یک ابزار انتخاب کنید.\n2. فایل یا لینک را اضافه کنید.\n3. نتیجه را بخوانید." if fa else
                        "1. Choose a service.\n2. Add your file or listing links.\n3. Read your result.")
    if role != "viewer":
        with st.sidebar.expander("ابزارهای تخصصی" if fa else "Detailed tools"):
            for section, key in zip(list(SECTIONS)[1:], ("pricing", "campaigns", "listings", "actuals", "costs", "sales", "changes")):
                st.button(section_label(section, language), key="tool_"+key, on_click=navigate, args=(section,))
    if task != "home" and role != "viewer":
        st.button("← خانه" if fa else "← Home", on_click=enter, args=("home",))
    if task == "home":
        st.title("امروز چه کاری دارید؟" if fa else "What would you like to do?")
        cols = st.columns(2)
        for i, (key, labels) in enumerate(SERVICES.items()):
            cols[i % 2].button(labels[fa], key="quick_"+key, icon=f":material/{labels[2]}:",
                               on_click=enter, args=(key,), width="stretch")
        cols[1].button("داشبورد پروژه" if fa else "Open project dashboard", icon=":material/folder_open:",
                       key="quick_dashboard", on_click=enter, args=("dashboard",), width="stretch")
        if history:
            st.subheader("آخرین بررسی" if fa else "Last review")
            st.write(history[-1]["source"])
            st.caption(history[-1]["time"])
        return
    if task == "dashboard":
        st.title("داشبورد پروژه" if fa else "Project dashboard")
        dashboard(history, bool(path), role, fa)
        return
    st.title(SERVICES[task][fa])
    st.sidebar.caption(DETAILS[task][fa])
    upload = st.file_uploader("فایل خود را اضافه کنید" if fa else "Add your file",
                              type=["xlsx", "csv", "pdf"], key="quick_input_"+task, max_upload_size=25)
    raw_links = ""
    if task == "listing" and upload is None:
        raw_links = st.text_area("یا لینک‌های محصول آمازون را وارد کنید" if fa else "Or paste Amazon product links",
                                 placeholder="https://www.amazon.ae/dp/…", key="quick_links")
    reuse = None
    if upload is None and not raw_links.strip():
        if not history:
            return
        latest = history[-1]
        reuse_key = (task, "saved", latest["fingerprint"])
        if st.session_state.get("quick_reuse") == reuse_key or st.button(
            ("استفاده از داده‌های آخرین گزارش" if fa else "Use the latest saved inputs"),
            help=latest["source"], key="reuse_"+task,
        ):
            reuse = latest
            st.session_state["quick_reuse"] = reuse_key
        else:
            return
    data = upload.getvalue() if upload else raw_links.strip().encode()
    name = Path(upload.name).name if upload else "Amazon product links"
    sheet = None
    if upload and name.lower().endswith(".xlsx"):
        sheets = workbook_sheets(data)
        if not sheets:
            raise ValueError("This workbook has no worksheets.")
        if len(sheets) > 1:
            sheet = st.selectbox("برگه" if fa else "Sheet", sheets,
                                 index=sheets.index("Products") if "Products" in sheets else 0)
        else:
            sheet = sheets[0]
    identity = (task, name, sheet, hashlib.sha256(data).hexdigest())
    if reuse:
        name = reuse["source"]
        identity = (task, name, None, hashlib.sha256(encode(reuse["inputs"])).hexdigest())
    last = st.session_state.get("quick_last", ())
    if last and last[0] == identity:
        show_review(last[1], fa, role)
        st.button("مشاهده پروژه" if fa else "View in project", on_click=enter, args=("dashboard",))
        return
    if not upload and not reuse and not st.button("خواندن لینک‌ها" if fa else "Read links", type="primary"):
        return
    if reuse:
        rows = reuse["inputs"]
        report = analyze(task, rows)
    elif upload:
        rows = file_rows(data, name, sheet)
        report = analyze(task, rows)
    else:
        rows, sources = source_links(raw_links)
        report = analyze(task, rows) if rows else {}
        report["Sources"] = sources
        if not rows:
            st.warning("خواندن صفحات ممکن نشد." if fa else "No product pages could be read. Upload your catalog or use a saved page in Detailed tools.")
            st.dataframe(sources, hide_index=True)
            return
    rev = revision(task, f"{name} · {sheet}" if sheet else name, rows, report)
    if path:
        team_history(path, role, new=rev, user=user)
    elif next_revision(history, rev):
        export_project([*history, rev])
        st.session_state["quick_history"] = [*history, rev]
    if reuse:
        st.session_state["quick_reuse"] = (task, "saved", rev["fingerprint"])
    st.session_state["quick_last"] = (identity, rev)
    show_review(rev, fa, role)
    st.button("مشاهده پروژه" if fa else "View in project", on_click=enter, args=("dashboard",))


def quick_workspace(language, team):
    try:
        render_quick(language, team)
    except (ValueError, PermissionError) as exc:
        st.warning(str(exc))
    except sqlite3.Error:
        st.error("Team storage is unavailable. Check the configured database folder.")
