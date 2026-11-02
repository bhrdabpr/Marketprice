# Architecture

`app.py` and `marketprice.cli` are adapters. Both call `io.read_upload → validation.validate → batch.process → io.workbook_bytes`. Core mathematics has no Streamlit, pandas, filesystem, or network dependency.

- `models.py`: frozen Pydantic contracts, currency precision and explicit fields.
- `config.py` + `rules/profiles.json`: versioned profiles and conflict checks.
- `engine.py`: ledger, progressive commissions, piecewise-affine floor solver.
- `recommendation.py`: explicit commercial selection and final feasibility check.
- `campaign.py`: seller/platform/shared funding and safety decisions.
- `currency.py`: optional explicit sourced conversion API.
- `validation.py`: locale parsing, aliases, missing/invalid diagnostics.
- `io.py`: bounded CSV/XLSX parsing and write-only workbook export.
- `batch.py`: row isolation, duplicate detection, scenarios, audit and reconciliation.
- `launcher.py`: readiness check and browser launch; shell and Windows wrappers.

Pandas is confined to interface previews/charts. Bulk calculation loops use Decimal objects per SKU to avoid float coercion. Write-only OpenPyXL avoids allocating millions of worksheet cell objects. Output records still consume memory; 100,000-row mode is CLI/batch on a provisioned machine, not unlimited streaming.

Profiles are immutable models, but callers must not mutate nested dictionaries. A run hashes the complete serialized profile set. Every row carries source row number and SKU; valid rows include normalized inputs and applied profile/version. Original data appears in Product_Calculations, errors stay visible, and no aggregate forecast adds different currencies or equates inventory with sales.

Browser sessions hold uploads/results in memory, without global data caching. The launcher binds localhost. Hosted operation requires a trusted access boundary; this app has no built-in user accounts. No external data calls are made by calculation modules. Streamlit telemetry is disabled in committed config.
