# Contributing

Set up Python 3.13 and install requirements-dev.lock. Use a feature branch and keep core finance separate from UI/import code. Add an independent worked example for any financial rule change, describe its fee/tax base and rounding policy, and include boundary/property tests where applicable.

Run pytest, ruff, mypy and pip-audit; run browser E2E for UI/import/export changes. Benchmark significant bulk/export changes. Update methodology, configuration version, changelog and known limits. Never weaken an assertion to match a new output without independent financial justification.

Do not submit real merchant data, credentials or unlicensed third-party code. Contributions are accepted under MIT; preserve dependency licenses. Do not label example schedules official or add marketplace tax rates without dated primary evidence and appropriate model support.
