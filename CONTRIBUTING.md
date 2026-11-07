# Contributing

Thank you for helping improve MarketPrice. Start with an issue describing the problem or proposed change, especially for financial rules or large changes. Keep core finance separate from UI and import code.

## Set up

Use Python 3.13, as in CI, and work from the repository root:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pytest -q
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`. Run the app with `.venv/bin/python launcher.py` (or `.venv\Scripts\python.exe launcher.py` on Windows). For the main user workflow, use the synthetic CSV in [samples](samples/sample_input.csv); the [case study](CASE_STUDY.md) explains its expected results.

## Before opening a pull request

- Explain the change, its motivation, and the checks you ran. Include screenshots for visual changes only after checking that they contain synthetic data and no private information.
- For financial changes, provide an independent worked example, specify fee and tax bases and rounding, and add applicable boundary or property tests. Never weaken an assertion just to match a new output.
- Run `python -m pytest -q`, `ruff check .`, `mypy marketprice app.py`, and `pip-audit -r requirements.lock` in the development environment. See [TESTING.md](TESTING.md) for browser tests and benchmarks; run browser tests for UI, import, or export changes and benchmark significant bulk or export changes.
- Update the methodology, configuration version, changelog, and known limitations when applicable. Do not call example schedules official or add marketplace tax rates without dated primary evidence and model support.
- Stage your changes, then run `python scripts/check_publication.py`. Review the staged diff and every image manually: this heuristic cannot identify all sensitive data.

## Privacy and security

Do not submit merchant data, credentials, personal information, or unlicensed third-party code. Keep private workbooks and generated reports outside the repository or in ignored directories. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md), rather than opening a public issue.

Contributions are accepted under the [MIT license](LICENSE); preserve dependency licenses.
