# Reproducible pricing case study

Run `PYTHONPATH=. python scripts/verify_case_study.py` from the repository with the project environment. All records are synthetic. This checks arithmetic independently of the engine's pricing solver; it is not an external audit.

Upload `samples/final-case-study.csv`. Map `selling_toman` to current selling price and explicitly select TOMAN → IRR for that column. All other money is IRR. Set the primary margin to 10%, additional margins to 15%;25%, discount to 10%, and confirm other costs are inapplicable only for this example.

Three rows produce two valid products and one isolated missing-commission error. Explicit zero commission on DEMO-003 remains valid. DEMO-001 selling price is 1,500,000 IRR after conversion; costs are 1,010,000 IRR, commission and seller-expense tax are each 10% of selling price.

Independent calculation: contribution = price × (1 − commission − seller tax) − costs. Thus current contribution is 190,000 IRR, break-even is 1,262,500 IRR, and rounded-up unit-grid floors for 10%, 15%, 25% margins are respectively 1,442,858; 1,553,847; 1,836,364 IRR. At a seller-funded 10% discount, price is 1,350,000 and contribution is 70,000 IRR; it remains above break-even but falls below a 10% margin.

A local three-row calculation took approximately 0.0034 seconds on this run. This excludes imports, export, browser time and concurrency. No manual-work saving has been measured.

## Three-minute demonstration script

0:00–0:30: State the pricing-floor promise and open the synthetic sample.
0:30–1:10: Choose language, mapping, IRR and explicit toman-column conversion.
1:10–1:40: Calculate; show two valid products and the single missing-commission correction.
1:40–2:20: Explain break-even and the three margin floors using the arithmetic above.
2:20–2:45: Show the 10% promotion's contribution and margin limitation.
2:45–3:00: Prepare/download the complete report; explain that fees are supplied by the seller and demand is not predicted.

Recording, fresh-user acceptance and genuine seller/accountant feedback are pending. Do not present this script as a completed video or independent review.
