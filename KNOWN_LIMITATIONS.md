# Current integration boundaries (1.6)

- Actual-profit inputs use the documented normalized schema, not certified Digikala/Amazon native exports.
- Fee evidence is seller-declared; caps, minimum fees, refund-specific fee rules and per-fee settlement rounding remain unsupported.
- Excel companion is experimental and not yet tested as a native button.
- Campaign comparisons are descriptive; there is no causal demand or optimal-price model.
- Approved manifests are not vendor upload files; live marketplace publishing is absent.
- Public hosting, multi-tenant isolation and background job infrastructure are not delivered.

The historical notes below describe earlier versions and may be superseded by [DEVELOPMENT_FLOW.md](DEVELOPMENT_FLOW.md).

## Version 1.2 additions

Flexible mode requires explicit file currency and margin settings; absent cost columns are treated as inapplicable under the displayed policy. Present blanks remain errors. Supported fee semantics are documented in FLEXIBLE_CATALOG.md; arbitrary new fee formulas still require implementation. The API is localhost-only and uses a development WSGI server. Marketplace adapters are a tested extension contract, not live Amazon/Digikala connections.

# Known limitations and release boundaries

No critical calculation defect is currently known **within the documented model** after the recorded tests. This is not universal production certification.

- Marketplace schedules are examples. No official Digikala, Snapp Shop, Amazon, eBay, Shopify or WooCommerce fee/tax policy was verified or imported.
- Only progressive marginal commission tiers, not retroactive whole-price tiers, minimum/capped fees or arbitrary nonlinear fee functions. These require new validated adapters.
- One full-transaction sales-tax base. No mixed taxable components, compound taxes, income tax or withholding accounting. Per-fee/per-tax cash settlement rounding is not modeled.
- User-entered expected return loss is a fixed expected cost. Returns/refund event probabilities and recoveries are not calculated automatically.
- Maximum-discount fields describe seller-funded campaigns only. Shared/platform funding is available in explicit simulations. Under nonmonotone tiers, test each actual discount; a maximum limit is not a blanket guarantee.
- Optional explicit currency conversion is a developer API, not an upload/UI conversion workflow. Never mix monetary units in a row. The currency registry is deliberately finite.
- Profile editing requires JSON; the UI selects profiles but does not provide a visual rule editor. Category campaigns may use separate profile IDs. Baseline financial inputs are conservatively required even if a profile ignores a fallback field.
- Price floors are bounded at 1e18; prices are positive grid points. No profit-maximizing market model, live competitor ingestion or marketplace write-back exists.
- UI previews show at most 1,000 records. Inputs are capped at 25 MiB/100,000 rows/80 columns; large files should use CLI and adequately provisioned memory. The 100,000-row benchmark measures one batch, not multi-user hosting.
- Local single-user application: no authentication/tenancy, durable job queue, hosted monitoring or production penetration test. The development API is localhost-only. External deployment needs a secured access boundary.
- Docker, fresh Windows/Linux installation, native double-click OS integration and native Excel rendering were not verified here. GitHub Actions passed on Linux for published commit 7719a599e94e2ee21853d9bbff038f5292085e2b. Source is published at https://github.com/bhrdabpr/Marketprice. No public application service exists.
- Development and runtime versions are pinned; lock files are not wheel-hash manifests. Dependency scan results are time-specific.

Resolve applicable limitations and verify real seller contracts before using outputs to publish live prices. A model-specific reviewed pilot is appropriate; unconditional universal production-readiness claims are not.
