# Marketplace profiles

All eight profiles (`generic`, `custom`, `digikala`, `snapp_shop`, `amazon`, `ebay`, `shopify`, `woocommerce`) are deliberately labeled **illustrative**, dated 2026-11-02, version `example-1`. They do not contain official fee schedules. Currency, shipping responsibility/cost, fulfillment amounts, sales tax and percentages must be explicitly supplied per row. Seller shipping zero is valid only when seller responsibility is confirmed zero.

Edit `marketprice/rules/profiles.json` for the UI, or use CLI `--rules path.json`. The file is a JSON list validated against `Profile`. Unknown keys, duplicate IDs, invalid rates and conflicting tier rules fail. `required_fields` can additionally require normally optional fields. Baseline cost/tax requirements cannot be disabled. This conservative contract avoids silent omissions.

Fee bases: `net`, `gross`, `list`, `settlement` (see methodology). Progressive tiers are marginal, not retroactive whole-price brackets:

```json
"tiers": [{"up_to":"100","rate":"0.10"},{"up_to":null,"rate":"0.20"}]
```

The first 100 units of the selected commission base cost 10%; only the excess costs 20%. Boundaries must increase and the final tier must be unbounded. `category_tiers` maps category IDs to the same structure and overrides default tiers. The row commission_rate is still required as explicit fallback but ignored when a tier schedule applies. Flat fee remains additive. Campaign fee override and tiers are mutually exclusive; category-specific campaign treatment can use separate profile IDs.

`subsidy_taxable` must be explicit. `campaign_fixed_fee` must be explicit even when zero. `campaign_commission_rate=null` means use the ordinary commission schedule. Recovery of fee tax and purchase input tax are separate row inputs.

When adapting real fees, record the authoritative source, effective date and version in the profile description/source fields, preserve the original contract evidence outside this repository, and add independent golden fixtures. The model intentionally prevents marking bundled example profiles official. Consult the actual applicable seller contract and tax treatment; this program does not establish them.

Limits: full-transaction taxable base only; no compound tax, income/withholding, retroactive tiers, minimum/capped fees, or item/order basket allocations. Unsupported structures need a new tested adapter, not an approximate equivalent rate.
