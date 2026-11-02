For the new flexible mode, start with [the simple catalog walkthrough](FLEXIBLE_CATALOG.md). For API usage see [API.md](API.md).

# Test MarketPrice in five minutes

1. Start launch.command (macOS), launch.bat (Windows), or launch.sh (Linux), then open localhost:8501.
2. Upload samples/sample_input.xlsx and calculate: two valid rows, one invalid row, golden price 117.65 USD.
3. Upload samples/5_costs.xlsx. Enable Configure applicable costs for this workbook. The app selects the five cost columns present. Confirm they match your intended model; absent unselected costs are inapplicable.
4. Calculate: COMPLETE and ZERO-COMMISSION must be valid; MISSING-COMMISSION must be invalid. Download results and verify the Errors sheet identifies only the missing-commission product.
5. Repeat with samples/10_costs.xlsx and the ten selected cost fields. The same row-isolation outcome must hold.

Tax settings, purchase cost, currency and pricing objectives remain required regardless of cost scope. Never declare an absent charge inapplicable just because its amount is unknown. All present cost columns are validated even if unselected.

Automated equivalents: pytest tests/test_cost_scope.py -v; full suite: pytest. Synthetic samples only; do not upload merchant data to the public repository.

Excel examples are generated locally rather than stored in this public repository. After installing dependencies, run `PYTHONPATH=. python scripts/generate_samples.py` from the project root. This creates the sample input/output and five/ten-cost workbooks from synthetic Python data. The sample CSV is also available directly.
