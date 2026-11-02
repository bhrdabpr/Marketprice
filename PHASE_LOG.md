# Execution checkpoints

This log records work actually performed in this session. It does not imply separately committed historical phases or an independent external audit.

| Phase | Files / outcome | Verification |
|---|---|---|
| 1 Discovery/research | EXISTING_SYSTEM_AUDIT.md, RESEARCH_AND_BUILD_VS_FORK.md | Empty workspace confirmed; five public commerce repositories and selected code/license/test directories inspected, not executed |
| 2 Specification | FINANCIAL_METHODOLOGY.md, models.py, MARKETPLACE_CONFIGURATION.md | Explicit tax/revenue, fee bases, units and validation contracts reviewed against mission |
| 3 Core | engine.py, precision.py, currency.py | Golden equation, tax/fee fixtures and independent tier-grid property tests |
| 4 Bulk I/O | validation.py, io.py, batch.py, samples/ | XLSX roundtrip, malformed input, duplicates, literal-text export and 1,000 independent rows |
| 5 Campaign/recommendation | campaign.py, recommendation.py | Shared funding, exact seller-funded maximum discount, minimum/cap enforcement and unsafe override tests |
| 6 UI | app.py | Streamlit AppTest and actual Chromium file input / download |
| 7 Debugging | tests/, reports/pytest.* | Parser, precision-context and UI rerun defects corrected; final full-suite report records final count |
| 8 Performance/security | scripts/benchmark.py, reports/benchmark-*.json, dependency-audit.json | Three batch sizes measured; dependency scan rerun after pip update; input security tests |
| 9 Packaging | launchers, Dockerfile, compose.yaml, locks, CI | POSIX launcher and CLI executed; Docker/Windows/Linux remain unverified |
| 10 Audit | FINAL_QA_REPORT.md, browser-e2e.json | Independent manual equations, retained invalid row, all ten downloaded sheets, actual screenshots |
| 11 Publication preparation | README, license, security/contribution docs, Persian guide, demo/LinkedIn draft | Local repository/package only; no public posting, push or deployment |

The final pass extended exact campaign limits to list/fixed campaign fee rules, made financial contexts independent of caller settings, and flattened original/audit inputs into readable columns. Tests and benchmarks were rerun after these changes. Formatting-only and documentation changes were checked separately.
