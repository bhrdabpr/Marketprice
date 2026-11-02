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
