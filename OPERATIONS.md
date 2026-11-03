# Actual profit and settlement workflow

Select **Actual profit (سود واقعی)** in the app. Start with the synthetic CSVs in `samples/operations/`, set reporting date to 2026-11-01 or later, review the signs and completeness checkbox, and analyze.

The fixture produces Digikala contribution **800 IRR**, Snapp contribution **850 IRR**, a **20 IRR** expected-fee discrepancy, and a **50 IRR** payout shortfall. These are synthetic examples, not real marketplace rates.

## Transaction schema

Required columns: `transaction_id`, `marketplace`, `currency`, `date`, `kind`, `amount`.

Sales additionally require text `order_id`, text `sku`, positive `quantity`. Optional fields: `settlement_id`, signed `expected_amount`, `due_date`, `payment_type` (`cash`, `credit`, `unknown`), and paired `campaign` / `phase` (`before`, `during`, `after`). Dates are Gregorian ISO `YYYY-MM-DD`; amounts accept Persian digits but must use the stated currency. Normalize toman to rial before importing this workspace. No implicit FX or Jalali conversion occurs.

| Kind | Sign | Profit | Settlement |
|---|---|---|---|
| sale | positive or zero | Revenue | Included |
| refund | negative or zero | Reduces revenue | Included |
| fee, advertising, tax | negative or zero | Expense | Included; these are marketplace-withheld charges |
| cost | negative or zero | Additional external expense | Excluded; use for external ads/logistics, never purchase COGS already in history |
| cost_recovery | positive or zero | Explicit recovered cost | Excluded |
| adjustment | signed | Affects profit | Included; use only understood income/expense adjustments |
| reserve | negative or zero | Excluded | Reduces available payout |
| release | positive or zero | Excluded | Increases available payout |
| payout | positive or zero | Excluded | Actual cash received; requires settlement ID |

Amounts must exclude collected VAT. Collected tax, loan principal and unknown adjustment types must be normalized appropriately before use; this schema is not a complete accounting ledger. Keep unknown transactions visible outside confirmed totals rather than assigning an arbitrary category.

Duplicate transaction IDs within a marketplace exclude **every occurrence** and leave a source error. Invalid input prevents complete aggregate claims. Missing settlement IDs, orphan refunds and unallocated fees remain visible. Settlements only show MATCHED when both activity and payout exist and exact amounts agree. This proves agreement within the extract, not that all external activity was supplied.

## Cost history

Columns: `sku`, `currency`, `effective_date`, `historical_unit_cost`, `replacement_unit_cost`, `source`.

Historical COGS uses the latest dated cost at or before each sale. Replacement contribution uses the latest cost at or before the reporting date. Missing or duplicate cost history prevents a complete contribution claim; it never becomes zero. Refunds retain original COGS unless an explicit `cost_recovery` records recovered value. Do not enter purchase COGS again as a cost transaction.

This is dated per-unit cost analysis, not inventory/FIFO/batch accounting. Source row references accompany each cost selection. Multi-product order fees remain at order level until supported allocation evidence exists; they are not arbitrarily split by SKU.

## Expected versus actual and campaigns

`expected_amount` is a user-supplied signed expectation for an individual transaction. The app flags differences; it does not derive all expected charges from a vendor contract. Campaign totals include only unambiguous, consistently tagged order groups. Compare coverage periods and unallocated account expenses before interpreting performance; there is no causal sales-uplift model.

## Seller rule bundles

`marketprice.contracts.load_contract` accepts an explicitly reviewed bundle containing seller_reference, currency, valid_from, valid_until, reviewed_on, reviewed_by, evidence_reference and profile. The profile uses the existing strict Profile schema. Currency and date mismatches, unknown fee terms and unsupported fields are rejected. The app records the bundle and content hash in the audit. Evidence is declared by the seller, not independently verified. Do not encode fee caps/minimums/refund rules that the engine does not support as if they were simple percentages.

## Approved updates

Pricing → Review price changes → select one scenario per product → confirm the current seller contract → download a JSON change manifest. It contains previous/new prices, floor, currency and result hash. It is **not** a certified marketplace import template and does not publish prices. Saved setups never contain merchant rows or credentials; they still need review when a marketplace changes the meaning of a column without renaming it.

The Product_Platform section compares single-SKU order groups across markets, with an explicit exclusion of unallocated shared costs. Settlement timing reports days from the first sale to the last payout within the supplied settlement group, not a guaranteed credit term or weighted cash-cycle forecast.
