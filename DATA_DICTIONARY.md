# Input data dictionary

One row is one independent SKU/order unit. Rates are fractions or explicit percent strings. All monetary inputs share the row currency. Unknown columns are rejected; map them explicitly.

| Field | Required | Definition |
|---|---|---|
| `sku` | Yes | Unique text identifier; keep leading zeros. |
| `name` | Yes | Unicode product name. |
| `marketplace` | Yes | Versioned profile ID. |
| `category` | Yes | Category ID used for tier overrides. |
| `currency` | Yes | Explicit monetary unit; TOMAN is distinct from IRR. |
| `current_price` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `purchase_cost` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `shipping` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `fulfillment` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `packaging` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `warehouse` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `overhead` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `advertising` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `other_fixed` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `expected_return_cost` | Yes | Explicit expected net return/refund loss per order; derive externally. |
| `marketplace_extra` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `commission_rate` | Yes | Explicit rate as fraction or percent text (0.10 or 10%); tax rules are user supplied. |
| `commission_fixed` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `payment_rate` | Yes | Explicit rate as fraction or percent text (0.10 or 10%); tax rules are user supplied. |
| `payment_fixed` | Yes | Explicit per-order amount in row currency; zero must be confirmed. |
| `other_rate` | Yes | Explicit rate as fraction or percent text (0.10 or 10%); tax rules are user supplied. |
| `transaction_tax_rate` | Yes | Explicit rate as fraction or percent text (0.10 or 10%); tax rules are user supplied. |
| `tax_rate` | Yes | Explicit rate as fraction or percent text (0.10 or 10%); tax rules are user supplied. |
| `tax_mode` | Yes | inclusive or exclusive; applies to all selling price values. |
| `input_tax_credit` | Yes | Recoverable tax included in purchase_cost; subtracted once. |
| `fee_tax_rate` | Yes | Explicit rate as fraction or percent text (0.10 or 10%); tax rules are user supplied. |
| `fee_tax_recoverable` | Yes | true: fee tax credit offsets fee tax; false: seller expense. |
| `target_margin` | Yes | Contribution/revenue fraction; 20% or 0.20, not 20. |
| `minimum_margin` | Yes | Mandatory regular/campaign minimum contribution margin. |
| `campaign_margin` | Yes | Campaign margin objective; mandatory minimum also applies. |
| `max_discount` | Yes | Maximum permitted customer discount fraction from current price. |
| `increment` | Yes | Positive multiple of currency minor unit; floors round upward. |
| `recommendation_rule` | Yes | floor, match_competitor, or keep_current. |
| `quantity` | No; omitted means unused | Optional inventory count, never used as a sales forecast. |
| `competitor_price` | No; omitted means unused | Explicit per-order amount in row currency; zero must be confirmed. |
| `price_ceiling` | No; omitted means unused | Explicit per-order amount in row currency; zero must be confirmed. |
| `price_minimum` | No; omitted means unused | Explicit per-order amount in row currency; zero must be confirmed. |
