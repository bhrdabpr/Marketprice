# Marketplace rules and product direction

Research date: 2026-11-04. Sources below are discovery references, not installed or certified rate bundles.

## Product thesis
MarketPrice should shorten repeated seller pricing reviews while connecting every proposed price to costs, dated contract rules, competitor evidence, and actual settlement. The portfolio value is a demonstrable chain of evidence and robust boundary tests. Commercial differentiation remains a hypothesis until measured in repeated seller pilots.

Price/sales map: X = observed price; Y = units per day; median reference lines within the same marketplace/category/currency. Growth compares equal adjacent periods. Margin status describes loss/target shortfall/unknown, not overall risk. The current map uses seller input, not scraped competitor sales. Different variants, stockouts, ads and seasonality prevent causal price conclusions. A cross-sectional regression is not a price elasticity model.

## Rule acceptance checklist — every marketplace
- [ ] Record marketplace country, seller plan, category/variant mapping, fulfillment mode and currency.
- [ ] Record source URL/document, retrieved date, effective-from/to dates, and seller exceptions.
- [ ] Specify calculation base, fixed/percentage/minimum/maximum/tier behavior and whether tiers are marginal or whole-price.
- [ ] Specify grain: unit, order, shipment, listing, storage-day or account period. Do not duplicate order fees across products.
- [ ] Separate shipping to customer, seller-to-warehouse transport and processing.
- [ ] Specify VAT/tax base, exemption, recoverability and rounding stage independently for each charge.
- [ ] Include discounts, marketplace funding, credit payments, refunds, cancellation and advertising attribution.
- [ ] Test below/at/above every threshold, tax and currency conversion, missing categories, conflicting dates and duplicate charges.
- [ ] Match independent worked examples and a private real statement. Record unexplained residuals.
- [ ] Only after review activate a dated bundle; missing applicable rules must remain incomplete.

## Prioritized sources and remaining work
| Priority | Marketplace | Official source discovered | Remaining work |
| --- | --- | --- | --- |
| 1 | Digikala | https://selleracademy.digikala.com/ ; https://t.me/s/Digikala_Marketplace | Academy returned 403. Obtain accessible current category/cap schedule and seller terms. Invoice ratios do not establish caps or universal rates. |
| 2 | Amazon US, then separate countries | https://sell.amazon.com/pricing ; https://sellercentral.amazon.com/help/hub/reference/external/200336920 | Category fees, minimums/tier semantics, FBA size/weight/storage, refunds, tax, effective dates. |
| 3 | eBay US, then separate countries | https://www.ebay.com/help/selling/fees-credits-invoices/selling-fees?id=4822 ; https://www.ebay.com/help/fees-billing/sell-fees-payments/store-selling-fees-managed-payments-sellers?id=4809 | Store plan/category, amount basis including applicable shipping/tax, per-order charges, performance surcharges and ads. |
| 4 | Etsy | https://help.etsy.com/hc/en-gb/articles/360035902374-Etsy-Fee-Basics | Listing/renewal, transaction, country-specific payment processing and offsite ads. |
| 5 | Walmart US | https://marketplacelearn.walmart.com/guides/Getting%2Bstarted/Onboarding/Referral-fee-schedule-for-contract-categories | Category/contract fees, WFS, price incentives; official guide located in search, detailed schedule not yet validated. |
| 6 | Basalam, Torob, Noon, other requested markets | No verified fee source installed | Discover official seller documentation first; distinguish marketplaces from CPC traffic channels. |

No numeric official bundle was installed from these search results. Support for every tax and law is not claimed.

## Implementation sequence
1. Current local checkpoint: visible workspace navigation, restrained blue/grey/black UI, reduced-motion support; observed price/sales chart and export.
2. Verify category-specific capped shipping/processing and commission rules with contract evidence; supply a guided rule editor and boundary preview.
3. Harden native invoice parsing for multi-item orders, duplicate IDs, blank rows, quantity, reversals and tax provenance before wider certification.
4. Build repeat-review queue: changed costs, expired rules, below-floor prices, conflicting evidence, then approved draft changes.
5. Use actual inventory-days, matched offer snapshots and authorized Buy Box eligibility/history; no winner guarantees.
6. Model price response only with sufficient longitudinal data, availability/ad controls, holdout validation and uncertainty intervals. Run bounded seller-approved experiments.
7. Observe two review cycles per pilot; measure repeat time, corrections confirmed, false flags, unexplained settlement difference and willingness to pay.

## Design references
https://linear.app/insights — modular analytics, filters and access to underlying evidence.
https://ramp.com/ — finance workflows organized around concrete tasks.
These are information-architecture references, not claims that MarketPrice has their capabilities or a copied design.
