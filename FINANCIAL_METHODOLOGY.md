# Financial methodology — model 1.0.0

This is a contribution-pricing model, not income-tax accounting, legal advice, or demand optimization. All monetary inputs for a row share one explicit unit. Prices, competitor constraints and campaign discounts use the row's `tax_mode`. Costs are cash amounts including any nonrecoverable tax. No exchange rates are inferred.

## Revenue, costs and tax

Let P be the transaction price, t the sales-tax rate, S the platform subsidy, and L the regular list price (`current_price` for campaigns). Tax-exclusive pricing: customer gross=P(1+t), customer net=P. Inclusive pricing: customer gross=P, customer net=P/(1+t). The entire product transaction is the sales-tax base; mixed taxable/exempt components are unsupported.

A taxable subsidy uses the same inclusive/exclusive units as P; inclusive net subsidy=S/(1+t), exclusive net subsidy=S. If configured nontaxable, all S is revenue and no subsidy tax is collected. Revenue R=customer net+net subsidy. Collected tax is reported separately and excluded from profit. `settlement` fee base is customer gross plus net subsidy plus subsidy tax; `net` excludes subsidy, `gross` excludes subsidy, `list` uses the original price in its declared inclusive/exclusive units. These are deliberate definitions, not marketplace policy claims.

COGS=purchase_cost-input_tax_credit. Input credit must already be included in purchase_cost and cannot exceed it. Other per-order costs are shipping, fulfillment, packaging, warehouse, overhead, advertising, other_fixed, expected_return_cost, and marketplace_extra. All require explicit values, including zero. Expected return cost is a user-estimated net loss; stochastic refunds and reverse logistics are not automatically modeled.

Commission = percentage fee (or progressive tier sum) + fixed commission. Payment = chosen base × payment_rate + payment_fixed. Other variable cost = chosen base × other_rate. Fee tax applies to commission plus payment; the recoverable portion equals all of this fee tax when `fee_tax_recoverable=true`, otherwise zero. Transaction tax = R × transaction_tax_rate and is a seller expense, **not income or withholding tax**.

Total cost = COGS + per-order fixed costs + commission + payment + other variable cost + fee tax − fee tax credit + transaction tax. Campaign-specific fixed fee is added only during campaigns. Contribution profit=R−total cost. Contribution margin=profit/R; undefined when R=0. Markup=profit/total cost; undefined when cost=0. These quantities deliberately differ.

## Price floors and recommendations

For the simplified zero-tax example, 80/(1−.10−.02−.20)=117.6470588235…; upward cent rounding produces **117.65**, profit **23.532**, margin above 20%. Break-even is **90.91**. At 117.64 the target is missed.

Regular-price solving enumerates progressive commission segments. Within each segment, profit−target×revenue is affine. Its root is rounded upward to the permitted increment and reevaluated. Both increasing and decreasing marginal tier rates are supported. No bisection assumption of globally monotone margin is required. Prices above 1e18 are outside the model and reported as unavailable; this is a numerical domain limit, not a proof of impossibility over arbitrary real numbers. Zero-cost products still require at least one positive increment to define margin.

Recommendations apply the selected `floor`, `keep_current`, or `match_competitor` rule, the mandatory minimum margin, optional marketplace minimum and ceiling, and upward increments. The final price is reevaluated after constraints. A constraint conflict produces no final recommendation. Competitor matching never deliberately breaches the cost floor. Multiple margin scenarios are independent; unavailable optional scenarios generate warnings. No claim of profit-maximizing price is made.

## Campaigns

Percentage and fixed discounts are measured from current/list price. The customer price rounds upward to the currency minor unit, so actual discount never exceeds requested discount. Platform share of the actual discount is the subsidy (0=seller funded, 1=platform funded). The same fee-base definitions apply; a profile may replace flat campaign commission and add a fixed campaign fee. Category tiers apply during campaigns too. Tiered commission and flat campaign override cannot be combined.

Safety requires nonnegative profit, defined margin at least max(minimum_margin,campaign_margin), and actual discount within max_discount. Override can approve a simulated unsafe campaign but never changes `safe=false` or its warning. No prices are posted to marketplaces.

Seller-funded maximum discounts solve the actual campaign fee model, including fixed campaign charges and list-price fee bases. The minimum-margin limit also enforces the maximum permitted discount. Candidate prices use currency minor units and are restricted to the current-price interval. Null means no feasible discount, including zero, meets the requested constraints. Tiered schedules with nonmonotone margin require checking the actual campaign; a maximum limit is not a guarantee for every intermediate discount.

## Precision and units

All financial functions use a fresh Decimal context with 50-digit precision and half-even arithmetic, independent of caller precision/rounding settings. Inputs parse from decimal text; no binary float arithmetic drives the solver. Price increments must be multiples of configured minor units. Exact Decimal output with more than 15 significant digits is exported as literal text, preventing silent Excel precision loss; shorter values are numeric cells. There is no per-fee settlement rounding: markets that round each fee/tax separately need a separately validated adapter before live use. This model is not a payout reconciliation ledger.

Supported units: USD, EUR, GBP, AED, SAR, CAD, AUD, CHF (2 decimals); IRR, TOMAN, JPY, KRW (0); KWD, BHD (3). Unsupported units fail validation. `currency.Conversion` provides an optional developer API requiring an explicit rate, source and timezone-aware timestamp, with half-up target-unit rounding. It does not automatically convert uploaded rows. Rates, costs, ceilings and increments must be converted together externally; never mix them in one row.

## Independent checks

Tests contain the manual example above, inclusive/exclusive 20% tax equivalence, input/fee credits, shared-funded subsidy tax, all four fee bases and independently enumerated tiered integer grids. Property tests state their monotone flat-fee preconditions. See TESTING.md and reports for executed results.
