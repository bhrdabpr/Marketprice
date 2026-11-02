# Testing and evidence

Install `requirements-dev.lock` into an isolated environment. Run from the repository root:

```sh
python -m pytest -q --junitxml=reports/pytest.xml
ruff check .
mypy marketprice app.py
pip-audit --format json --output reports/dependency-audit.json
PYTHONPATH=. python scripts/generate_samples.py
PYTHONPATH=. python scripts/benchmark.py --rows 1000
PYTHONPATH=. python scripts/benchmark.py --rows 10000
PYTHONPATH=. python scripts/benchmark.py --rows 100000
```

For browser testing, install Chromium using `python -m playwright install chromium`, run the local app, then run `PYTHONPATH=. python scripts/browser_e2e.py`. The script uploads a real XLSX through the file input, clicks Calculate, downloads the resulting workbook, independently checks 117.65 and the retained invalid row, and saves actual screenshots. It does not substitute direct API calls for browser upload.

Unit/golden coverage includes margin versus markup, zero/missing costs, flat/fixed/progressive/category fees, tax modes and credits, four fee bases, currencies/rounding, impossible targets, subsidies, unsafe campaigns, malformed data, duplicates, and very large prices. Workbook tests inspect all ten sheets, original row reconciliation and literal cell types. Security tests cover oversized uploads and external workbook links. Property tests cover flat-fee cost/target monotonicity, deterministic results, row-order independence, campaign safety, and independent finite-grid enumeration of progressive fees.

Financial expected values come from manual equations or independent finite-grid formulas, not the production evaluator. Precision comparisons use the same explicit Decimal context where they compare repeating quotients. Early failures included a leading-dot parser bug, a manually mistyped subsidy expected value (correct result 46.56), and a context mismatch in a repeating markup comparison. Those were corrected with explicit independent reasoning, not weaker assertions.

Streamlit AppTest timed out inside the restricted tool sandbox; the identical test passed outside it. The real local browser workflow also passed. A download-induced transient rerun initially confused a strict Playwright tab locator; download buttons now use `on_click="ignore"`. Debug logs preserve these earlier failures separately from the final suite report.

Static analysis covers application/core source with mypy check_untyped_defs, not strict typing of every helper or proof of correctness. Dependency scanning initially found vulnerabilities in pip 25.0.1; upgrading the isolated environment to 26.2.2 produced a clean scan. No penetration test or third-party financial certification was performed.

Benchmark generation varies purchase cost, shipping, commission and selling price per SKU. Export is included. `scripts/benchmark.py` asserts row reconciliation and absence of input errors. Browser performance for 100,000 rows and peak memory profiling are not established by this benchmark. Native Microsoft Excel/LibreOffice rendering was not available for verification; structural XLSX checks were executed with OpenPyXL.
