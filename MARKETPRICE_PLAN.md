# MarketPrice execution plan — 2026-11-04

## Product decision
Serve Iranian and Amazon/eBay sellers with one local decision core and separate marketplace adapters. Build an evidence-backed daily/weekly review, not an unsupported claim to outperform marketplaces at their own demand data. The initial user is an owner/operator or accountant with a catalog, costs and transaction exports.

The repeatable workflow is: import → resolve missing facts → compare current, replenishment and campaign economics → review an action → export evidence → reconcile the outcome. An internet outage must not prevent calculation with local inputs. Live observations retain dates and stale status; no outage silently becomes “no competitors.”

## Current baseline and limits
Public source is 74e9a57 (settlement source 80d1012). Unpublished session/layout/download/math fixes have been inspected and preserved; 208 local tests pass. Local-first means no runtime cloud inference or marketplace connection is required for existing calculations. It does not mean a fresh machine can install dependencies offline: an offline installer/wheel bundle and clean-machine checks are still needed.

The code has a read-listings adapter protocol, not functioning Amazon/eBay/Digikala integrations. Marketplace mapping profiles are examples, not certified fee schedules. Existing actual-profit and dated-cost analysis is a useful foundation, but native export matching and expected-to-actual joins remain unverified.

## Current benchmark shortlist
Reviewed official/vendor material on 4 November 2026. These are best-fit references by workflow, not a universal “best software” ranking or independently tested performance comparison. Availability, account eligibility and payment from Iran have not been verified; no VPN, account or legal-access workaround is assumed.

| Reference | Capability to learn from | Implication |
|---|---|---|
| [Amazon Automate Pricing](https://sell.amazon.com/tools/automate-pricing) | Rule-driven repricing with price bounds | Generic repricing is already native; costs and policy bounds must precede action |
| [Amazon Product Opportunity Explorer](https://sell.amazon.com/tools/product-opportunity-explorer/) | Search/purchase and niche-level research | MarketPrice cannot infer demand from a few competitor prices |
| [Amazon Seller Assistant](https://sellingpartners.aboutamazon.com/seller-assistant) | Seller-context insights and permissioned actions | A chat interface alone is not differentiation |
| [eBay Product Research](https://www.ebay.com/help/selling/selling-tools/terapeak-research-and-SEO?id=4853) | Sold prices, shipping, condition filters, historical research | Separate asking prices from actual sales and match product/condition before comparing |
| [sellerboard](https://sellerboard.com/) | COGS/profit, returns, inventory, PPC and repricing | Contribution and cost provenance are required across workflows |
| [Helium 10's Helium agent](https://www.helium10.com/blog/introducing-the-helium-super-agent-that-runs-your-amazon-business/) | Cross-tool diagnosis across research, ads and commerce | Agents need normalized evidence and tools, not invented answers |
| [Jungle Scout AI Assist](https://support.junglescout.com/hc/en-us/articles/17206297711127-AI-Assist-Chat) | Knowledge/business assistance; documented accuracy limits | Retain source references and durable decisions rather than disposable chat |
| [Amazon Manage Your Experiments](https://sell.amazon.com/tools/manage-your-experiments) | Listing tests with eligibility/traffic requirements | Marketing should define hypotheses and measure outcomes; generated copy is not evidence of uplift |

[eBay's advertising documentation](https://developer.ebay.com/api-docs/sell/static/marketing/pl-overview.html) separates cost-per-sale and cost-per-click campaigns. Its CPS basis can include shipping and taxes. Our generic “other_rate” must not be marketed as a certified eBay ads adapter. [Amazon fee estimates](https://developer-docs.amazon/sp-api/lang-en_en/docs/get-product-fee-estimates-sku) require seller authorization and a relevant developer role; estimates must remain distinct from actual deducted fees. [eBay Marketing API](https://developer.ebay.com/api-docs/sell/static/marketing/marketing-seller-inventory.html) has account/subscription requirements. No live access is available or claimed here.

For Iran, the [Digikala seller channel](https://t.me/s/Digikala_Marketplace) highlights financial-panel, deduction and settlement questions. [Seller360](https://seller360.ir/accounts/welcome/) advertises broad repricing/profit/settlement tools, so localization alone is not uniqueness. Current seller contracts and authorized extracts must decide supported rules.

## Specialist workflows (agents as product roles)
These are planned product capabilities, not spawned assistants or existing autonomous services. Numerical answers must come from the deterministic financial engine. Optional language models may explain a validated result or draft content, never calculate authoritative fees, invent evidence or publish prices.

| Role | Inputs | Output | Boundary |
|---|---|---|---|
| Data reviewer | Files, mapping, identifiers, units | Missing/ambiguous fields and evidence requests | Never silently fill unknown cost with zero |
| Pricing reviewer | Contract model, current costs, dated replacement quotes | Floors, contribution differences, constraint conflicts | No automatic claim that a lower price sells better |
| Campaign planner | Unit contribution, baseline volume, extra spend, seller scenarios | Required sales, sensitivity, checklist | Requirement is not demand forecast; no combined currencies |
| Reconciliation reviewer | Orders, charges, payouts, prior decision snapshot | Explained differences and unresolved residuals | No forced balancing or invented allocation |
| Market researcher | Timestamped comparable offers and sold-data extracts | Comparable range, missing evidence, research hypotheses | No Buy Box prediction without validated model/data |
| Marketing reviewer | Product facts, traffic, clicks, attributed orders, spend | Listing/ad hypotheses and measurement plan | Attribution is not incremental uplift; never invent product claims |
| Execution controller | Approved proposal, fresh input snapshot, account permissions | Dry-run diff, receipt, verification, reversal plan | Writes separately enabled; budget/price caps, idempotency and stop control required |

## Milestones in order

### 0 — Preserve and verify current local fixes
- [x] Inspect handoff/diff and preserve uncommitted edits.
- [x] Re-run current suite: 208 tests pass.
- [ ] Finish previously blocked manual viewport/upload-clear verification before public release claims.

### 1 — Shared replacement-cost and campaign decision pack (implement now)
- [x] Seller quote template tied to the current calculation snapshot, row, SKU, marketplace and currency.
- [x] Date/source/amount validation; expired, future, duplicate, mismatched and missing quotes cannot masquerade as usable evidence.
- [x] Compare current/campaign contribution with replacement net acquisition cost; re-solve target floor through the existing fee engine, retaining constraints and provisional cost status.
- [x] Single-product campaign budget comparison: baseline units and additional campaign spend → units required to preserve contribution. No demand forecast or portfolio aggregation.
- [x] Bilingual UI, exact JSON evidence, no source-data mutation or price publication.
- [x] Independent arithmetic, identity/freshness, currency, no-network and UI/export regression tests.

### 2 — Contract evidence and native import adapters
Start with one authorized seller/category/export version per market; do not guess based on marketplace name.
- Capture seller/account + marketplace site + fulfillment + product variant + currency + tax basis.
- Version fee rules and source evidence, effective dates, min/cap thresholds, shipping and per-charge rounding.
- Map native exports with explicit sign conventions, transaction IDs and completeness windows; reject duplicate/ambiguous joins.
- Acceptance: invoice examples and threshold boundary cases signed off by seller/accountant; synthetic equivalents public, originals private.
Gate: representative contracts/exports and eligible account/API access are not currently supplied. Keep CSV/XLSX/manual paths usable when online sources are unavailable.

### 3 — Expected-versus-actual reconciliation and review queue
- Link an approved scenario snapshot to subsequent transactions and payouts.
- Separate price, units, fee changes, refunds, ads, replacement costs and settlement differences.
- Sort review work within each currency by documented impact; show unresolved reasons.
- Acceptance: every residual explained or explicitly unresolved, no arbitrary SKU allocation, repeat imports idempotent.
Depends on milestone 2's identifiers and native semantics.

### 4 — Professional marketing measurement
- First add importable funnel/ad metrics with date range, attribution definition and data completeness.
- Diagnose low impressions versus low click-through versus low conversion versus low contribution.
- Compute ACoS/ROAS/TACoS only with stated denominators, consistent periods, attribution windows and zero-denominator handling.
- Draft one experiment at a time: hypothesis, audience, offer/listing change, spend cap, stopping rule, success metric and confounders.
- Acceptance: a genuine measured experiment and contribution outcome. Never infer causality from before/after alone.

### 5 — Offline packaging and optional connected execution
- Lock and bundle dependencies for a selected OS; test clean-machine install and disconnected operation.
- Queue read syncs; maintain freshness and provenance; retries/backoff, pagination, partial-data flags and scoped credentials.
- Start with read-only authorized APIs; then dry runs. Live price/ad writes require explicit account authorization, caps, idempotency, audit receipts and recovery tests.
- Optional local or hosted language model remains replaceable; core calculations and evidence exports must work without it. No merchant data sent to hosted models by default.
Gate: chosen target OS and account credentials/eligibility, not speculative connectors.

### 6 — Pilot and commercial gate
Use one eligible pilot per intended market, but validate the first deeply before expanding. Two review cycles each; record setup/repeat time, confirmed mistakes caught, false flags, unallocated residuals and whether the seller will pay for another review. Numerical targets are negotiated with pilots, not presented as achieved. Use evidence to reorder later milestones.

## What to build less of
Do not chase broad inventory/CRM/order-management parity, a crawler, guaranteed demand prediction or a universal fee table. The proposed advantage is portability, explicit uncertainty, reproducible calculations, private working data, and a connected trail from quote to decision to settlement. This remains a hypothesis until tested against sellers' existing workflows.

## Execution record
Milestone 1 implemented locally: replacement.py and replacement_ui.py, bilingual quote and budget evidence. Full suite: 244 tests passed; subsequent quote-change confirmation regression passed in both languages. Ruff and mypy35 passed before final UI state refinement; final targeted checks recorded in TASK_STATE.md. No hosted CI/publication or final live browser verification claimed.
First pilot selected by user: Digikala. Next input needed: seller-specific current fee/fulfillment terms and an authorized transaction/settlement extract for one period. No credentials needed for file-based validation.

Digikala native invoice checkpoint implemented locally on 2026-11-04. The adapter reconciles native summary/detail sheets, extracts file-observed rates, converts Jalali dates, preserves account-level charges as unallocated, and exports schema-compatible transactions. A private sample reconciled to zero difference and exposed a VAT label/amount mismatch; the app reports it without installing a universal rule. Synthetic tests only are stored in the repository. Full suite 247 passed; Ruff and mypy36 passed. Still needed: dated purchase costs, bank/payment evidence, more categories and exception cases before certification.
