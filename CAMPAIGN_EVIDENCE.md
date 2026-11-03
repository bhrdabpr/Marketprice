# Campaign decision passport

The product promise is a traceable decision: can this entered campaign meet the configured cost/margin checks, and how does its delivered price compare with fresh, seller-confirmed equivalent offers? This is a useful differentiation hypothesis, not an exclusive feature claim or proof of willingness to pay.

## Input requirements
Use the CSV template in samples/competitor-evidence.csv. It deliberately has an old date so it cannot masquerade as current market evidence.

- sku/marketplace/currency must identify the same product context as the calculation.
- product_reference identifies the exact model/variant; match_confirmed and available must be true. These are seller declarations, not independently verified matches.
- offer_condition and our_condition must be nonempty and equal.
- competitor_delivered_price includes the customer-facing delivery charge. our_customer_delivery_charge is what YOUR customer pays, not your shipping expense.
- observed_at must include a timezone, be no more than24hours old, and not lie in the future. The24hour window is a documented product policy, not a marketplace guarantee.
- source_url must be HTTPS without embedded login credentials. URLs are recorded; the app does not fetch them.

Missing, stale, mismatched or malformed evidence is rejected with reasons. Financially unsafe or cost-provisional campaigns cannot become ready merely because a competitor is cheaper. Review outputs say WITHIN_OBSERVED_PRICE or ABOVE_OBSERVED_PRICE, with the price gap. Among multiple accepted observations, comparison uses the lowest supplied delivered price; this is not a complete market survey.

## Evidence and limits
Download the passport JSON to retain the supplied observations, timestamp, source links, calculated review and calculation snapshot hash. It is separate from the14-sheet pricing workbook. Formula snapshots and price-dependent charges require owner review and supported fee rules. The workbook scanner detects direct references, not transitive formulas, named ranges or INDIRECT dependencies.

No current workbook field is assumed to be a competitor or BuyBox observation merely because it contains a marketplace selling price. No predicted conversion, uplift, winning probability, causal campaign impact or recommended automatic price write is produced.

Amazon itself describes price plus shipping and additional offer factors in its Featured Offer guidance: https://sellercentral.amazon.com/help/hub/reference/external/G201687550?locale=en-DE . Marketplace-specific mechanics must be separately verified.
