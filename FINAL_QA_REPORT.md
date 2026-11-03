# Version 1.5 verification — 2026-11-03

- 130 automated tests pass; Ruff and mypy (30 source files) pass.
- Persian synthetic multi-market catalog: Digikala produces two valid products and one isolated missing-commission error.
- Browser checks cover Persian result filters and rial-to-toman display; numeric exports remain unchanged.
- Channel selection scopes mapping suggestions, not live marketplace connections or verified seller contracts.

# Version 1.4 verification — 2026-11-03

- 123 automated tests pass, including new cost-confidence, saved-setup, approval, actual-profit, refund/reserve, duplicate, date and currency regressions.
- Ruff passes; mypy checks 27 source files.
- Browser minimal catalog: 3 products, 2 valid, 1 isolated missing-tax error; downloaded 14-sheet workbook independently checked, profitable prices retained.
- Synthetic actuals: contribution 800 / 850 IRR, fee variance 20 IRR, payout variance -50 IRR; app test exercises the actual-profit demo.
- 10,000 synthetic sale rows reconciled in 0.275 seconds locally (calculation only; not an export or concurrency benchmark).
- Pure Excel matrix bridge tested; native xlwings button certification is pending.
- Vendor template/contract certification, official price-upload formats, live API publishing, and causal campaign optimization are not claimed complete.

Historical verification follows.

# Version 1.3 verification

97 local tests passed; Ruff and mypy passed (20 source files). Independent numerical tests reconcile three margin floors, break-even, increase/decrease/keep decisions and margin-constrained seasonal discounts. New optional cost fields are included in the ledger and preserve present-blank product errors. Twelve report sections now include Price_Analysis and Seasonal_Campaigns. The browser workflow verifies three normal margin scenarios and both default seasonal reports. Current hosted results are available under GitHub Actions. Research sources, assumptions and worked examples are in COST_GUIDE.md.

## Earlier release evidence

# Version 1.2 verification — 2026-11-02

86 local tests passed; Ruff and mypy passed (17 source files). A real browser uploaded the minimal CSV, calculated 2 valid/1 invalid products, and downloaded an independently reconciled workbook (125 IRR recommendation, 35 IRR current profit for the first row). An actual localhost HTTP POST returned 200 and the same pricing result.

A synthetic 10,000-product catalog with eleven cost fields produced 9,999 valid and one invalid product in 2.074 seconds, with XLSX export in 12.581 seconds (2,286,458 bytes). This scenario has no current prices, so campaigns are intentionally absent; it is not comparable to the earlier full campaign benchmark. See reports/flexible-10000.json. Marketplace adapter tests use fixtures; no live vendor API is connected. Hosted CI for this revision should be checked on GitHub Actions.

## Earlier release evidence

# Final QA report — 2026-11-02

**Release assessment: tested local application and model-specific release candidate. Universal production readiness is NOT VERIFIED.** The scoped acceptance checks below pass with the stated evidence. Production deployment, marketplace-specific legal/contract correctness, and unsupported financial models are not inferred from those passes.

No existing project was supplied. This was a clean implementation, with original MIT-licensed source and no copied upstream engine code. At the initial local audit, no public repository push, deployment or LinkedIn post had been performed. Subsequent source publication and hosted CI results are recorded below.

## Mandatory acceptance checks

| # | Criterion | Status | Actual evidence / qualification |
|---|---|---|---|
| 1 | Core pricing independently verified | PASS | Golden 117.65 example, tax fixtures, and independent tier-grid enumeration; tests/test_engine.py and tests/test_adversarial.py |
| 2 | Missing required fields produce SKU errors | PASS | Missing cost/commission/shipping/tax tests; sample ERROR-003 retained |
| 3 | Explicit zeros work | PASS | Parameterized zero-cost/rate tests |
| 4 | Marketplace rules independent of engine | PASS | marketprice/rules/profiles.json and Profile validation; engine contains no marketplace name branches |
| 5 | Multiple target margins | PASS | Multiple-scenario test and browser-generated 15%/20%/25% rows |
| 6 | Campaign constraints enforced | PASS | Seller/platform/shared funding, negative profit, minimum margin, discount caps, explicit unsafe override and exact limit tests |
| 7 | Tax and fee assumptions auditable | PASS | Ledger, normalized audit columns, rule versions/hash, FINANCIAL_METHODOLOGY.md |
| 8 | At least 1,000 realistic product rows | PASS | 1,000 distinct cost golden checks; varying-cost/rate benchmark at 1k, 10k and 100k |
| 9 | Actual UI Excel upload | PASS | Chromium 156.0.8078.4 file-input upload; reports/browser-e2e.json |
| 10 | Downloadable workbook | PASS | Actual browser download saved and parsed; ten required sheets |
| 11 | Output reconciles independently | PASS | Browser and unit golden price 117.65; independent tax/fee equations |
| 12 | Invalid rows stay visible | PASS | Three sample inputs → three output rows, two valid, one invalid; missing shipping error |
| 13 | Automated tests pass | PASS | 64 passed in 1.70s; reports/pytest.txt and reports/pytest.xml |
| 14 | Static and dependency/security checks run | PASS | Ruff clean; mypy clean across 14 source files; pip check clean; pip-audit no known vulnerabilities |
| 15 | Performance benchmark executed | PASS | reports/benchmark-1000.json, benchmark-10000.json and benchmark-100000.json |
| 16 | Local launch workflow tested | PASS | macOS launch.command using installed isolated environment; localhost health endpoint and browser use; reports/local-launch.log |
| 17 | Deployment artifacts/instructions exist | PASS | Dockerfile, compose.yaml, pinned requirements, health check, launchers, DEPLOYMENT.md; container execution separately unverified |
| 18 | Documentation and samples delivered | PASS | README, methodology, rules, dictionary, architecture, testing/security/contribution docs, Persian guide, sample XLSX/CSV and output |
| 19 | No known critical calculation defects remain | PASS | No known failures in the declared supported model after final tests; unsupported models are explicitly excluded, not claimed correct |
| 20 | Unverified criteria identified | PASS | Environment and operational verification table below plus KNOWN_LIMITATIONS.md |

## Unverified and restricted release areas

| Area | Status | Reason / required next verification |
|---|---|---|
| Docker build and container operation | NOT VERIFIED | Docker executable unavailable; deployment artifacts exist, but image build, Linux dependency resolution and container upload/download remain to be run |
| Windows/Linux native launch; fresh install bootstrap | NOT VERIFIED | Available host was macOS; POSIX launcher used an existing isolated environment. No native executable was built |
| Native macOS double-click browser opening | NOT VERIFIED | Launcher was invoked from shell with --no-browser; application readiness and browser access passed |
| Native Excel/LibreOffice visual rendering | NOT VERIFIED | Workbook structure, values, literal cells, filters and frozen headers checked with OpenPyXL; native desktop spreadsheet renderer not exercised |
| Public hosted deployment, authentication, concurrent tenancy | NOT VERIFIED | No public service deployed; requires protected hosting, monitoring and operational review |
| GitHub Actions hosted execution | PASS | Linux hosted run 41429942389 passed installation, lint, typing, tests, dependency audit, benchmark, generation and browser upload/download |
| Official marketplace/tax rules and settlement reconciliation | NOT VERIFIED | Bundled profiles are examples; no contract-specific fee/tax certification or per-fee rounding adapter |
| 100,000-row browser interaction and peak memory | NOT VERIFIED | CLI-style calculation/export benchmark completed; browser only tested with sample workbook; peak RSS not measured |
| Broad arbitrary fee/tax coverage | NOT VERIFIED | Unsupported structures are listed in KNOWN_LIMITATIONS.md; do not approximate them with unverified rates |

## Final measured performance

Measured calculation plus workbook export on macOS 26.6.2 ARM64, Python 3.13.3. Synthetic rows vary purchase cost, shipping, commission and selling price. These are measurements on one host, not SLAs. The final audit-column format is wider than early exports; the values below supersede earlier progress estimates.

| Rows | Calculation (s) | Export (s) | Total (s) | XLSX bytes |
|---:|---:|---:|---:|---:|
| 1,000 | 0.257 | 2.508 | 2.765 | 937,908 |
| 10,000 | 4.006 | 25.659 | 29.665 | 9,217,345 |
| 100,000 | 28.213 | 251.691 | 279.904 | 92,548,887 |

The 1,000-row target is met. The final 100,000-row workbook is approximately 92.5 MB and takes about 4.7 minutes; use CLI and adequate memory or split into 10,000-row batches. Upload-size and expanded-archive limits still apply. No claim is made that the default 2 GiB Docker limit is sufficient for this workload.

## Financial reconciliation

- Golden tax-exclusive case: cost 80; variable rates .10+.02; target .20. Independent floor 80/.68, upward cent price 117.65, contribution 23.532. One cent lower fails the target.
- Progressive tier fixture: first 100 at 10%, excess at 20%, fixed cost 80, no payment fee. In upper segment profit=.8P−70; 20% target gives P=116.666…, rounded 116.67.
- Shared-funded inclusive case: regular 120, discount 20%, platform share 50%, tax 20%. Customer 96→net80; subsidy12→net10; commission8; total base cost80; contribution2.
- Campaign fixed/list-base fixture: current140, commission on list14, extra campaign fee5, base cost80 and payment2%. At 10% margin, .88P=99→112.50.
- Test expectations are derived from independent equations/grid enumeration; no separate external auditor was engaged.

## Security and reliability evidence

`reports/dependency-audit.json` records a clean installed-environment vulnerability scan after upgrading pip 25.0.1 to 26.2.2. This is database-based scanning, not penetration testing. `reports/pip-check.txt` confirms dependency consistency. Upload/schema/formula protections have automated coverage. Runtime code has no external product-data calls or embedded credentials.

Initial failures and their corrections are described in TESTING.md. A sandbox-only Streamlit test timeout passed under the same assertions outside the sandbox. The final full suite and real Chromium workflow both pass. Final screenshots were visually inspected and show synthetic sample data.

## Deliverable location and operation

The repository root contains app.py, launcher.py and platform launchers. Run launch.command on macOS or follow README for manual installation. Docker users can use docker compose up --build, subject to the unverified container checks above. Samples are in samples/, actual evidence in reports/, screenshots and demonstration/LinkedIn drafts in docs/. Git history contains local source and delivery checkpoints. No deployment URL is invented.

**Operational decision:** suitable for a reviewed local pilot within the documented financial model. Do not label it an unconditionally production-ready universal marketplace system until the applicable unverified deployment and seller-contract checks are completed.

## Publication update: 1.1.0

Workbook cost selection and five/ten-cost tests added. Full suite: 64 passing tests. Live-server restart is required after module changes to avoid stale Streamlit imports. Course eligibility is not claimed; see CREDITS.md.

Public-repository packaging: Excel artifacts are excluded from publication. Recreate synthetic examples locally using scripts/generate_samples.py. Private merchant data remains outside the repository. Both five/ten-cost examples were exercised through the live UI; the five-cost downloaded workbook was reconciled.

## Verified GitHub publication

Source: https://github.com/bhrdabpr/Marketprice. Published implementation commit: 7719a599e94e2ee21853d9bbff038f5292085e2b. [Hosted Linux CI](https://github.com/bhrdabpr/Marketprice/actions/runs/41429942389) completed successfully for every step. Local full suite: 64 tests passed in 1.72s. Five/ten-cost UI scenarios each produced two valid products and one isolated missing-commission product; five-cost downloaded rows and error codes were independently checked. Docker and Windows/native-launch verification remain outstanding. No public hosted app is claimed.
