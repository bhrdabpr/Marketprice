## Review columns after upload

Column mapping opens automatically and preserves your original headers. Persian/English names receive editable suggestions with sample values. Unknown names must be mapped or explicitly ignored. For workbooks with both Digikala and Snapp columns, choose the marketplace first; the other marketplace and recognized historical calculations are excluded in the suggested mapping. Review this before calculating.

Choose As entered for fractional rates (0.10) or percent text (10%). Choose Percentage number only when numeric 10 means 10%. For monetary inputs in toman with output currency IRR, choose TOMAN → IRR on those columns. Present blank/FALSE cells remain individual product errors. The seller tax default is a separate setting when no tax input column exists. Confirm the reviewed mapping to enable calculation. The export records source mapping and conversions.

Recognition uses a local dictionary and Unicode normalization, including common Persian/Arabic character variants. It does not send merchant data to an AI service or promise to understand every header. Unknown meanings require human review. This workflow currently assumes one header row and one product per row in the selected Products/first worksheet.

# Simple and company catalogs

Flexible catalog mode is on by default in the UI. Choose currency and target margin once in the sidebar, then upload `.xlsx` or `.csv`. Column order and product category do not matter. Use Column mapping for your own headers; select Ignore column for descriptive fields that do not affect pricing. Product rows still need a purchase cost.

## Minimum file

| purchase_cost | other_fixed |
| --- | --- |
| 100 | 10 |
| 200 | 20 |

Here `other_fixed` represents a fixed tax amount per item. With IRR and a 10% target margin, the first floor is **123 IRR**: `(100 + 10) / (1 - .10)`, rounded upward to a whole rial. Do not put a percentage into a fixed-cost column. If you also have other fixed expenses, combine them explicitly or use a separate available fixed-cost field.

For a tax equal to 10% of selling price, use `transaction_tax_rate` = `10%` instead. A purchase cost of 100, 10% seller tax and 10% margin gives **125 IRR**. `tax_rate` is collected sales tax and has a different treatment; it is not the seller expense field.

## Missing versus inapplicable

- A cost column absent from the whole file is declared inapplicable (zero) under the displayed flexible-mode policy. It is recorded in Assumptions.
- A column included anywhere applies to the entire catalog. A blank, missing JSON key, invalid number or boolean in a required cost field invalidates only that product.
- A numeric zero is a valid explicit value.
- Purchase cost cannot be omitted. Currency and margin use the sidebar defaults only when their whole columns are absent; present blanks remain errors.
- Missing SKU/name columns receive row identifiers/labels. Present duplicate or blank SKUs are still errors. Use persistent SKUs when connecting marketplace data.
- Supported optional informational fields such as quantity retain their existing optional semantics.
- No selling price column means floor calculations only; add current_price for actual current margin and campaign analysis. No campaigns are fabricated from a zero placeholder.
- Multiple currencies retain their own units; there is no implicit foreign exchange or TOMAN-to-IRR conversion. Convert explicitly before combining costs. One toman is ten rial.

Fourteen supported cost fields cover shipping, fulfillment, packaging, warehouse, overhead, advertising, other fixed costs, expected return cost, marketplace extras, percentage/fixed commission, percentage/fixed payment fee and other percentage fees. Tax components are separate. Choose any subset, including eleven costs for a company catalog. New fee types with different calculation bases require extending the model rather than mislabeling a field.

Use strict mode by turning off Flexible catalog when every financial field must be explicitly provided. Existing strict CLI behavior remains unchanged.

## Try it

1. Open the app and leave Flexible catalog enabled.
2. Upload `samples/cost-and-tax.csv` for the two-column example: 2 valid products.
3. Upload `samples/minimal.csv`: 3 products, 2 valid, 1 with missing seller tax. Its valid neighbors still receive prices and campaigns.
4. Download results and inspect Errors, Price_Recommendations, Campaign_Simulations and Assumptions.

CLI equivalent:

```sh
python -m marketprice.cli samples/cost-and-tax.csv results.xlsx --flexible --currency IRR --target-margin '10%'
```

The supported input limit is 100,000 rows / 25 MiB. A regression test covers 10,000 products with eleven included costs and one incomplete product. Inventory is not a prediction of sales, and a safe campaign means it meets the configured contribution/discount constraints, not that it will increase demand.
