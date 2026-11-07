# MarketPrice

## [▶ Open MarketPrice](https://marketprice-bhrdabpr.streamlit.app/)

Use it in your browser—no GitHub account or installation needed. The online demo processes files on its server; use synthetic or non-confidential data. It may take a moment to wake up.

[![Financial and workflow checks](https://github.com/bhrdabpr/Marketprice/actions/workflows/ci.yml/badge.svg)](https://github.com/bhrdabpr/Marketprice/actions/workflows/ci.yml)

**Review prices, promotions and settlement costs from your sales spreadsheet.**

Outputs assess financial feasibility under supplied costs and rules. They do not predict sales or identify optimal market prices.

Turn a seller’s cost spreadsheet into explainable price floors, three margin scenarios and promotion checks. Review incomplete products individually, then export the calculation evidence.

**Local-first · English / فارسی · Excel and CSV · Open source**

[Open the live app](https://marketprice-bhrdabpr.streamlit.app/) · [Try the synthetic case study](CASE_STUDY.md) · [Five real-data workbook checks](docs/WORKBOOK_VALIDATION.md) · [راهنمای فارسی](UI_GUIDE.fa.md) · [Financial limits](KNOWN_LIMITATIONS.md) · [What is ready for customers?](COMMERCIAL_READINESS.md)

The public app requires no GitHub account to use. Select USD, EUR, IRR or TOMAN for your file. The optional manual converter uses your entered exchange rate and does not change catalog values. The public app processes uploads on the hosting server. Use the local launcher for confidential catalogs. After an idle period the free host may ask you to wake the app.

**Downloadable Mac and Windows apps are not available yet.** For the current demo and the work needed for private hosting and desktop releases, see [Hosting and downloads](HOSTING_AND_DOWNLOADS.md).

## Is it for you?

MarketPrice is for a seller or accountant reviewing recurring price and discount decisions from a cost spreadsheet. It is useful when mixed units, missing costs and several margin scenarios make a workbook difficult to review. For a small, stable catalog with trusted formulas, Excel may remain simpler.

| Your question | What you get |
|---|---|
| Which products need correction? | Product-specific missing-field errors; other products still calculate |
| What price covers my entered costs? | Break-even and three chosen contribution-margin scenarios |
| Can this discount preserve profit? | Unit contribution, margin limits and the sales multiplier needed to preserve baseline contribution |
| Is this offer competitive? | Comparison against fresh, seller-supplied comparable delivered prices, with evidence and rejection reasons |
| What do returns and slow-moving stock cost? | Estimate reverse shipping, write-offs, storage and penalties per dispatched unit |
| Which products sell faster at different prices? | Compare observed sales velocity within a comparable group and optionally fit a descriptive trend |
| How does the payout compare to the statement? | Review normalized transactions or a supported Digikala invoice and export reconciliation evidence |
| Can I explain the decision? | Compact CSV, complete Excel audit and an optional campaign decision passport |

A campaign requiring 1.25× sales needs 25% more units to preserve contribution under the same cost assumptions. **MarketPrice does not predict those sales.**

## Try it in five steps

1. Launch locally and use [the public synthetic sample](samples/sample_input.csv) or generate the example Excel files with `PYTHONPATH=. python scripts/generate_samples.py`.
2. Select your language, sales channel, worksheet and monetary units. Review suggested column meanings.
3. Confirm costs and margin targets. Explicit zero means no expense; blank mapped costs invalidate that product. Unconfirmed omitted costs keep decisions provisional.
4. Calculate. Review corrections, price scenarios and one promotion before opening specialist analyses.
5. Download the compact summary; prepare the full Excel report only when you need it.

The standard sample has two valid products and one missing-shipping error. Its independently checked 20% target floor is **117.65 USD**. [Reproduce the calculation](CASE_STUDY.md).

## Run locally

Install Python 3.12+ (tested here with 3.13.3). On macOS, double-click `launch.command`; on Windows, use `launch.bat`; on Linux, run `./launch.sh`. First launch installs pinned dependencies into `.venv` and requires internet. Subsequent calculations work offline. The launcher starts a localhost server and opens your browser. Keep its terminal running; Ctrl+C stops it. macOS may require opening the script from Terminal if local security policy blocks double-click execution.

Manual equivalent:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python launcher.py
```

Windows manual commands use `.venv\Scripts\python.exe`. If installation fails, inspect the terminal error; the launcher does not silently continue. The macOS launcher execution was tested with an existing isolated environment; fresh dependency bootstrap and native double-click behavior on every OS are not claimed tested.

[Reproducible synthetic case study](CASE_STUDY.md) · [Completion checklist](FINISH_CHECKLIST.md)

## Iran-market development

Start with [the evidence and ranked work list](IRAN_MARKET_PLAN.md). Iranian repricing competitors exist; we do not claim an empty market or a unique invention.

In **Campaigns → What if settlement is delayed?**, enter additional days and your annual capital-cost assumption. Confirm these costs are not already counted. Compare current and campaign contribution, then download the assumptions and calculation evidence. Defaults are zero, not marketplace payment terms. [Model and example](SETTLEMENT_SCENARIOS.md).

## Know the boundaries

- Marketplace names provide **column-matching support**, not official fees or live connections. Enter your verified contract rules.
- These are expected contribution calculations, not audited accounting profit. Unsupported fee caps, minimums and complex tax rules must not be approximated silently.
- Explicit saved-value mode can read externally linked workbooks without executing formulas or fetching links. Cached values can be stale; detected selling-price-dependent costs remain provisional.
- No competitor crawling, guaranteed BuyBox win, demand optimization or automatic price publishing.
- This is a local/private-review tool. Public multi-tenant hosting, commercial validation and independent financial review remain unfinished gates.

## Privacy

Keep customer workbooks and results local. The repository contains synthetic examples. Local launch processes uploads in the local server session; **Clear session data** clears app state, not existing downloads or OS storage. Never put merchant records in public GitHub issues. [Security and publication policy](SECURITY.md) · [Public repository review](docs/PUBLICATION_REVIEW.md).

## Explore only what you need

- **Sellers:** [Five-minute walkthrough](QUICK_TEST.md), [bilingual costs guide](COST_GUIDE.md), [competitor evidence](CAMPAIGN_EVIDENCE.md).
- **Managers:** [Case study](CASE_STUDY.md), [financial methodology](FINANCIAL_METHODOLOGY.md), [customer-readiness review](COMMERCIAL_READINESS.md).
- **Developers:** [Architecture](ARCHITECTURE.md), [local API](API.md), [testing](TESTING.md), [deployment limits](DEPLOYMENT.md), [contributing](CONTRIBUTING.md).
- **Specialist workflows:** [Actual-profit and settlement imports](OPERATIONS.md), [experimental Excel companion](excel/README.md). These require additional setup and are outside the main pricing journey.

## Project status

Version 1.8.0 with subsequent fixes documented in [the changelog](CHANGELOG.md). See [QA evidence](FINAL_QA_REPORT.md) for exactly what was tested; tests are not marketplace certification. Fresh OS installs, native Excel integration and a recorded customer acceptance review are not claimed verified.

An AI-assisted Python portfolio project by [bhrdabpr](https://github.com/bhrdabpr), developed while studying Python. Not represented as an approved CS50P submission. [Credits](CREDITS.md). MIT licensed.

## Repeat a catalog review

In **What changed?**, upload an earlier complete MarketPrice report and the latest complete report. Match the same marketplace, SKU, variant and currency. The review shows recorded per-unit revenue, cost and contribution differences with source row references. Within each currency, the largest contribution decreases appear first. Missing confidence evidence requires review and duplicate identities block matching. The downloadable review includes source file hashes. These differences use the assumptions recorded in each report, so check fee rules and cost allocation before attributing a change to business performance. Review volume separately when estimating total monetary impact.
