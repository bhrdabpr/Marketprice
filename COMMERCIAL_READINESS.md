# MarketPrice: paid-readiness review — 2026-11-03

## Verdict
A verified local pricing model and a reproducible demonstration exist. A subscription business, hosted multi-tenant SaaS and autonomous agent service have not been validated. The number of tests establishes evidence about defined behavior, not willingness to pay or correctness of seller contracts.

## Why a seller might leave or refuse to pay

| Finding | Evidence / type | Treatment |
|---|---|---|
| Repeating a saved setup can change comparison margins or campaign choices | Code inspection: settings schema omitted these fields | Fixed locally; saved extra margins, discounts, type and platform funding now restored. Old setups remain compatible. Seasonal settings and legacy CSV encoding still need explicit review. |
| Full reports are too heavy for a quick decision | Existing full-XLSX benchmark; on-demand generation already avoids blocking calculation | Added optional compact CSV containing price scenarios and invalid products. Exact original data and full audit remain available in complete Excel. |
| Financial data cannot be explicitly cleared in the interface | Session-memory model, no clear-session action | Added clear-session control, tested across cached result/download reset. This does not erase existing downloads, OS caches, swap or infrastructure logs. |
| Customer must still prepare and verify costs | Current column mapping, cost confidence and seller inputs | Keep uncertainty visible. Pilot includes assisted setup; do not claim complete profit from incomplete costs. |
| Marketplace names can suggest ready-made financial integrations | Channels are mapping conveniences | Existing interface explains fees are seller-supplied. Certify one actual template/contract before advertising native support. |
| A price floor alone is easily reproduced in Excel | Product capability comparison | Sell repeated review, trustworthy correction and less preparation only after measuring them; avoid a generic calculator subscription claim. |
| Hosted service lacks accounts, tenant isolation, storage policy, job controls, billing and production operations | Deployment documentation and local-only API | Not ready for public multi-user exposure. Choose service audience and hosting model before implementation; private pilot first is the default recommendation. |
| No demonstrated repeat purchase or seller sign-off | Acceptance checklist | Must be observed with real customers. Do not invent testimonials, recovered money or time savings. |

## Proposed paid pilot, not a validated offer

Customer: seller or accountant who revisits a product cost file regularly before price changes or promotions. Deliver one reviewed setup, correction list, margin comparison and repeat review after costs change. Fees, data permissions and deliverables are agreed directly with the pilot seller. Do not promise optimal demand-based pricing or marketplace write-back.

Observe the customer's current workflow, then measure time to first usable result, preparation effort, false flags, verified useful findings and whether they return and pay for the next review. Suggested continuation gate: three pilot sellers complete a second review and at least two choose to pay. These are proposed decision thresholds, not market statistics.

## Tests and measurements

137 automated tests passed; Ruff and mypy30files passed. New regressions cover saved scenario choices, summary inclusion of invalid products, literal-text protection, omission of original audit columns, and explicit clearing of cached results/settings.

For 1000 synthetic products with one scenario each, compact export alone took 0.0028 seconds and produced 62937 bytes locally. Excludes calculation, import, browser, complete XLSX, concurrency and hosting. No universal speed or XLSX improvement claim.

CSV profit/margin describe each scenario's normal_price; they are expected contribution under entered costs, not realized accounting profit. Blank values and decision_ready must be reviewed. Invalid source rows are retained. CSV summary omits original merchant columns and technical audit payloads; use the full Excel for complete evidence.

## Market evidence

Sellerboard already advertises profit analytics, repricing and reimbursement tools: https://sellerboard.com/ . A2X offers traceable order-to-cash matching and financial exceptions: https://www.a2xaccounting.com/subledger . These demonstrate existing competitors, not unmet local demand. Local willingness to pay and contract/import coverage remain unverified.

## Delivery status

The fixes in this review are incorporated into version1.7 source. No public multi-user deployment is claimed. No screenshot publication: user explicitly declined it. Hosted SaaS or API rollout awaits a delivery decision and actual operational verification.
