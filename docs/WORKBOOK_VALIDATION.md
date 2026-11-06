# Historical workbook validation

On 6 November 2026 we exercised the Excel pricing workflow at application commit `d3cd702` with five input workbooks derived from three public sources. The inputs contain 193 product or bid lines. A Chromium session uploaded each prepared workbook through the local app, applied the margin settings and downloaded the complete Excel report. The checks reconciled every exported SKU, target and price against an independently calculated cent-rounded result. These are historical observations. A seller adopting a target, fee schedule or campaign still needs their own costs and terms.

| Source and selection | What the records establish | Result |
|---|---|---|
| Oregon DOT 2023 bid workbook, first 60 positive bid lines | Quoted unit acquisition amounts from a prospective buyer's perspective | 180 provisional floor prices |
| Oregon DOT 2024, same selection | A second annual file in the same format | 180 provisional floor prices |
| Oregon DOT 2025, same selection | A third annual file in the same format | 180 provisional floor prices |
| Five Iowa historical invoice lines shown in the first sample table | The state's bottle cost, price charged, units and transaction amount | 15 provisional floor prices and five 10% discount simulations |
| UCI Online Retail, UK “JUMBO BAG” lines on 1–2 December 2010 | Observed units and selling prices, with acquisition cost missing | All eight price recommendations blocked. Eight products usable for comparing sales velocity. |

## What was checked

**Price floors.** In the Oregon workbooks, read the BID DATA sheet below its actual header row. Divide extended amount by quantity and round to cents. Preserve the item, contract, unit and source row. A bid is a quoted amount. It establishes neither an invoice paid by the buyer nor the contractor's own cost. In the Iowa sample, check line amount against units times unit price and use state cost as the acquisition input. With the other costs unspecified, calculate floors for 10%, 20% and 30% margins. For each of the 555 results check that the proposed price equals cost divided by one minus the target margin, rounded upward to a cent. Keep these results provisional.

**Promotions and financing.** For all five Iowa lines compare the discounted price to 90% of the source price rounded upward to a cent, and compare unit contribution to discounted price less source cost. Also run a hypothetical ten-day settlement delay at 36.5% simple annual financing. The additional cost should equal 1% of acquisition cost. These rates are test inputs. The source supplies no seller financing contract, comparable live competitor offers or dated replacement quotes.

**Sales evidence.** Filter the UCI workbook by country, dates and product description. Keep the 50 matching source lines in the local case file, omitting customer identifiers. Use positive units and prices for gross sales velocity. Compare the two consecutive days, take the second day's quantity-weighted selling price rounded to cents, and retain eight products with positive second-day sales. Check daily units and weighted prices against the transaction lines, and compare the fitted slope against an independent least-squares implementation. Margin stays unknown. This two-day sample checks arithmetic and provides insufficient evidence to forecast demand.

**Replaying a case.** In Pricing & campaigns use a custom sales channel and select the Products sheet. Set the target to 20% and the other margins to 10% and 30%. Review mappings and currency, leaving absent costs unconfirmed. Prepare the complete Excel report and review Price_Recommendations, Errors and Cost_Confidence. For example, an Iowa line with USD 4.50 cost and USD 6.75 selling price gives a provisional USD 5.63 floor at 20%. The USD 2.25 spread precedes unreported expenses. Use the Sales sheet as CSV in Price & sales for the UCI case and set the period to one day.

## Evidence and coverage

- [Oregon Department of Transportation bid workbooks](https://www.oregon.gov/odot/business/pages/average_bid_item_prices.aspx). The three annual files share a schema and count as one source family.
- [Historical Iowa sample, table Out 5, Baur Safi](https://baursafi.github.io/project_2.html). The five published example lines date from 2015–2016. [Iowa Department of Revenue catalog](https://data.iowa.gov/catalog/dataset/1263) describes the state's more recent series.
- [Online Retail, D. Chen, UCI, CC BY 4.0](https://doi.org/10.24432/C5BW33). Local transformations include filtering, grouping and omission of customer IDs.
- [Automated checks for the tested release](https://github.com/bhrdabpr/Marketprice/actions/runs/42179162990). The suite separately covers fee boundaries, missing inputs, market-specific invoice parsing, bilingual workflows, security checks and browser downloads.

The public cases test observed prices, sales quantities and explicit assumptions. Seller net profit, fee caps under a current contract, realized campaign uplift and willingness to pay require separate seller evidence. Downloaded source workbooks and private seller records stay outside Git.
