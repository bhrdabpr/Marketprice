# Product costs, margins and seasonal pricing / هزینه کالا، حاشیه سود و کمپین

Research checked 2 November 2026. This is a practical taxonomy, not an exhaustive official fee schedule. Enter your own applicable costs. Marketplace/category/country contracts determine actual rates. Monetary costs are **per sold unit/order in the row currency**, not whole shipment or monthly totals. Allocate shared costs first; never count an expense again when it is already included in purchase cost or overhead.

| Stage | Costs to consider / هزینه ها | Supported inputs |
|---|---|---|
| Acquisition | Supplier purchase or manufacturing cost; materials and production labor / خرید یا ساخت | purchase_cost; labor only if not already in purchase_cost |
| Getting goods ready | Inbound freight, customs/brokerage/duties, insurance, inspection, certification / حمل ورودی، گمرک، بیمه، بازرسی، مجوز | inbound_freight, customs_duty, insurance, inspection, compliance |
| Capital and currency | Allocated finance/interest and bank/FX conversion fees / تامین مالی و تبدیل ارز | financing, currency_conversion |
| Storage and loss | Warehousing, handling, expected damage/shrinkage/spoilage / انبارداری، آسیب و کسری مورد انتظار | warehouse, expected_loss |
| Order delivery | Packaging, pick/pack/fulfillment, seller-paid delivery / بسته بندی، پردازش، ارسال | packaging, fulfillment, shipping |
| Marketplace/payment | Referral commission (fixed or percent), payment fees, listing/closing/subscription allocations / کمیسیون، کارمزد، هزینه بازار | commission_rate, commission_fixed, payment_rate, payment_fixed, marketplace_extra |
| Customer acquisition | Allocated advertising/acquisition cost and other percentage sales costs / تبلیغات و سایر هزینه های درصدی | advertising, other_rate |
| After sale | Expected net returns/refund/chargeback loss, warranty and support / مرجوعی، ضمانت، پشتیبانی | expected_return_cost, warranty, customer_support |
| Business operations | Allocated rent, staff, equipment depreciation, software/subscriptions, utilities and professional services / سربار، حقوق، استهلاک، نرم افزار، آب و برق | overhead, labor, software, utilities, other_fixed |
| Tax | Seller transaction-tax expense, collected VAT/sales tax, recoverable input/fee tax / هزینه مالیات فروشنده، مالیات دریافتی، اعتبار مالیات | transaction_tax_rate; tax_rate + tax_mode; input_tax_credit; fee_tax_rate + fee_tax_recoverable |
| Campaign | Existing expenses plus event-specific extra packing, advertising or fixed event fee / هزینه اضافه مناسبتی | each event's extra cost; avoid duplicating advertising/other_fixed already entered |

The thirteen new cost fields are optional when absent. A present blank remains a product-level error. Arbitrary capped/minimum fees, retrospective commission rules, regulated income-tax accounting and price-dependent external fee estimates still need a dedicated verified model. A flat per-unit allocation is an input estimate, not a live calculation of those rules. Financing is an entered allocation, not an interest schedule. Expected return/loss inputs are expected **net** costs, not whole refunded revenue plus the same lost goods again.

## Research sources

- [Amazon pricing](https://sell.amazon.com/pricing): selling/referral fees, fulfillment and optional programs; rates vary. No Amazon fee schedule has been imported into this app.
- [Amazon selling fees explanation](https://sell.amazon.com/blog/ask/fees-selling-on-amazon): advertising, promotion, fulfillment and storage cost categories.
- [Shopify product pricing](https://help.shopify.com/en/manual/products/dropshipping/creating-a-product-line/pricing-your-products): product and business expenses, marketing, subscription and transaction costs.
- [US International Trade Administration: total export price](https://www.trade.gov/determine-total-export-price): landed cost, freight, insurance, tariffs/taxes and broker charges.
- [US International Trade Administration: import fees overview](https://www.trade.gov/import-tariffs-fees-overview): duties and other landed costs depend on destination and goods.

These sources support the cost categories. Iranian seller rates/taxes remain merchant-provided; the example profiles do not claim official vendor rates.

## Break-even price and chosen margins

The app calculates **per-unit break-even selling price**, not a company-wide number of units to sell. With a single flat seller expense rate `r`, per-unit cost `C` and contribution margin `m`:

`break-even price = C / (1 - r)`

`target selling price = C / (1 - r - m)`

The real engine also handles configured tax bases, credits and progressive commission tiers. Prices round upward to the selected price increment and are re-evaluated. Margin is profit divided by revenue excluding collected sales tax, not markup on cost. Multiple currencies are not aggregated.

Set your primary target and two additional margins in the sidebar. For example, purchase cost 100 IRR and seller expense tax 10% gives break-even **112 IRR**, then **125 / 143 / 167 IRR** for margins **10% / 20% / 30%**. Rounding means actual achieved margins may slightly exceed targets.

Price_Analysis compares each normal-price scenario with the real current price: INCREASE / افزایش, DECREASE / کاهش or KEEP / حفظ. Without current price it reports SET_PRICE and does not invent a price change. A higher unit margin may reduce demand; the app cannot establish a profit-maximizing commercial margin without demand evidence. It offers auditable scenarios, not a sales forecast. Inventory columns are ignored by default in the UI.

## Seasonal campaigns

Choose Black Friday (جمعه سیاه), Christmas (کریسمس), Nowruz (نوروز) or Yalda (یلدا). Set the desired margin and extra cost **for each event**. No special date, demand uplift, official event discount or automatic price change is assumed.

The suggestion is the largest seller-funded discount on the currency grid that satisfies the event margin, product minimum margin, campaign fee rules and maximum discount. Actual platform funding is re-evaluated; funded campaigns may have room beyond this conservative seller-funded ceiling. The real current price is the reference; the app does not first raise a reference price to create an artificial discount. The final offer's actual margin and per-unit profit are included.

Example: cost 100 IRR, seller tax 10%, actual current price 200 IRR. An event with 5% margin and no extra cost suggests **118 IRR / 41% off**. Another with 10% margin and 20 IRR extra event cost suggests **150 IRR / 25% off**. A campaign that cannot satisfy its limits is marked NO_SAFE_OFFER. Equal assumptions produce equal prices across events. No current price means no campaign recommendation.

Normal recommendations and seasonal recommendations are separate report sections, so an increase required for normal profitability is not confused with a discount offer.
