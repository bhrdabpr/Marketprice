# MarketPrice development flow

**Promise:** Keep Excel as the working surface; turn seller data into traceable profit decisions with less repeated work.

## Ordered delivery

| Step | Concept | Current state | Evidence / next gate |
|---|---|---|---|
| 1 | Protect profitable prices and distinguish unknown costs from zero. | Implemented | Floors no longer trigger automatic reductions; missing/estimated costs block approval. |
| 2 | Review a template once and reuse its meanings and settings. | Implemented | Portable JSON mapping, units, tax and currency settings; changed headers require review. Semantic changes under identical headers still require human review. |
| 3 | Lead with actions and let users inspect the source evidence. | Implemented | Source-row action list, separate currencies, missing costs and loss checks. |
| 4 | Explain actual contribution and the difference between earnings and payout. | Implemented for normalized inputs | Transactions, refunds, reserves, costs and payouts; no invented joins; sample reconciles independently. Native vendor exports need fixtures. |
| 5 | Preserve historical costs while showing replacement economics. | Implemented | Dated per-SKU/currency history; original sale date vs reporting-date replacement view. This is not FIFO or inventory accounting. |
| 6 | Compare platforms and campaign periods without claiming demand causality. | Implemented, descriptive | Contribution, units, settlement exceptions, before/during/after totals; discount scenarios show required sales multiplier. Unequal exposure and unallocated costs remain limitations. |
| 7 | Approve a specific change against a specific calculation. | Implemented | One scenario per product, explicit contract acknowledgment, snapshot hash, previous/new price, no automatic publication. |
| 8 | Run the same engine from an Excel button. | Experimental bridge prepared | Pure matrix engine boundary tested; Excel/xlwings installation and real native button test still required. |
| 9 | Certify real marketplace imports, contracts and update exports. | Waiting for authentic, redacted fixtures | Seller-specific dated rule bundles supported; no official vendor format or contract claimed verified. Minimum fees, caps, refund policy and settlement rounding not modeled must block certification. |
| 10 | Add direct marketplace connections and measure paid customer value. | Not implemented | Seller API access, sandbox acceptance, secure hosting and pilot evidence required. |

## Daily user flow

Open workbook → reuse reviewed setup → validate product rows → inspect action list → compare historical/replacement contribution and settlements → review scenarios → approve selected changes → retain evidence.

On a first workbook, mapping and applicable-cost confirmation are essential. A single button can reuse an established setup; it cannot truthfully infer missing taxes, seller contracts or transaction completeness.

## Definition of success

Pilot with five sellers using a complete, redacted settlement period. Measure minutes spent before/after, verified deduction differences, missed-loss detection, repeat use and willingness to pay. Do not call a reconciled estimate recovered money until the marketplace confirms a correction. Do not call before/after differences campaign uplift without a valid comparison design.

## Release gates

- Financial tests include zero, blank, duplicate, malformed, date and currency boundaries.
- Every supported vendor template needs an anonymized fixture and control totals.
- Every fee contract needs source evidence, effective dates and covered/unsupported terms.
- New marketplace writes require bounds, explicit approval, observed response and a recoverable change record.
- Merchant files, identifiers, contracts and credentials never enter the public repository.
