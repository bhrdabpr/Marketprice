# 1.3.0 — Bilingual costs, price decisions and seasonal offers

## 1.5.0 — 2026-11-03

- Add selectable Persian/English interfaces, automatic RTL/LTR layout, readable local fonts and optional Persian digits.
- Add display-only IRR/TOMAN conversion with thousands separators; stored inputs, calculations, identifiers and downloads remain unchanged.
- Add All / Valid / Needs correction product pills; related calculations and errors follow the selected product rows.
- Put sales-channel selection before upload: custom website, Digikala, Snapp Shop, Tapsi Shop, Amazon, eBay, Shopify and WooCommerce.
- Automatically exclude other-channel columns, show an exclusion summary, and prioritize channel-relevant mapping fields with an advanced option.
- Preserve business settings when switching interface languages and simplify product/error summaries.
- Channel presets are import conveniences, not official fee schedules or live marketplace connectors.


## 1.4.0 — 2026-11-03

- Retain profitable current prices when a computed floor alone would suggest a reduction; competitor-driven decreases require review.
- Separate confirmed, confirmed-zero, estimated and missing cost declarations; absent costs yield provisional scenarios until confirmed.
- Add reusable JSON mappings/settings with header-drift detection and a prioritized source-linked action list.
- Add normalized transaction, refund, reserve, payout and dated-cost reconciliation, platform contribution and descriptive campaign-period totals.
- Show required campaign sales multiplier instead of claiming a demand optimum.
- Add dated seller-reviewed rule bundles and explicit snapshot-bound price approval manifests; no marketplace writes.
- Prepare an experimental xlwings Excel button bridge using the same pricing engine; native Excel certification remains pending.
- Preserve per-product catalog errors and literal-text exports; public samples remain synthetic.


- Thirteen optional per-unit cost categories, with present blanks still invalid.
- English labels followed by Persian translations, with bilingual header suggestions.
- Price_Analysis and Seasonal_Campaigns export sheets; primary plus two additional margin scenarios, per-unit break-even, price movements and configurable seasonal offers.
- Inventory ignored by default in the UI; no sales-volume forecast.
- Light grey theme, blue buttons, black body text and centered action buttons.
- 97 local tests pass, including independent numerical scenario/campaign checks. Research and worked examples: COST_GUIDE.md.

# Import mapping correction

- Visible, reviewable Persian/English header suggestions and sample values; unresolved columns block calculation before processing.
- Separate marketplace column selection, explicit units/rate conversions, ignored historical results, seller-tax default and exported mapping audit.
- 90 local tests pass; original Test2 workbook now maps directly for either marketplace with the same validated counts as the prior audit. Real merchant data stays local.

# 1.2.0 — Flexible catalogs and local pricing API

- File-wide currency/margin settings and absent-column cost scope, with row-level missing-value errors.
- Two-column examples, optional generated row IDs, explicit column ignore, and current-price-free floor calculations.
- Authenticated localhost JSON calculation endpoint and a tested vendor adapter protocol for future integrations.
- 86 local tests; 10,000-product/11-cost calculation and XLSX export verified. See reports/flexible-10000.json.
- Live marketplace connectors deferred; no seller credentials or vendor fee assumptions added.

# Changelog

## 1.1.0 — 2026-11-02

Added explicit workbook cost scope in UI and CLI. Absent inapplicable cost columns may be omitted; present blanks still fail only the affected SKU. Added five/ten-cost isolation regression tests and synthetic walkthrough files. Publication credits disclose AI assistance and course submission limits.

## 1.0.0 — 2026-11-02

Initial independently implemented release: Decimal ledger and progressive fee solver, strict row validation, tax/fee separation, rule-based recommendations, campaign simulations, source-preserving workbook export, Streamlit UI, CLI, example profiles, local launchers and deployment artifacts.

Included executed golden/property/integration/browser tests, measured 1,000/10,000/100,000-row benchmarks, static checks and dependency audit. See FINAL_QA_REPORT for actual release evidence and unverified deployment criteria. No public production deployment or marketplace certification is claimed.
