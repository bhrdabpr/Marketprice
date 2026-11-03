# Pricing API and future marketplace adapters

MarketPrice 1.2 provides a working **local calculation API**. Digikala and Amazon are future integrations, not connected services. No credentials or real seller data are included. Nothing changes marketplace listings automatically.

## Start the local API

After installing the project dependencies, run from the project folder:

```sh
export MARKETPRICE_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m marketprice.api
```

Keep that terminal open. Use the same token in the calling client (do not commit it). The service binds only to `127.0.0.1:8502`. It uses the standard-library WSGI development server, processes one request at a time, and is intended for local integration testing. Public hosting requires a production server, TLS, request timeouts, rate limiting and worker/memory limits. No CORS access is enabled.

`POST /v1/calculate`, with `Authorization: Bearer <your token>` and JSON:

```json
{
  "settings": {"currency": "IRR", "target_margin": "10%"},
  "products": [
    {"sku": "A", "purchase_cost": "100", "transaction_tax_rate": "10%", "current_price": "150"},
    {"sku": "B", "purchase_cost": "100", "transaction_tax_rate": "", "current_price": "150"}
  ]
}
```

The response uses the same twelve report sections as Excel. A has a recommended price of **125 IRR**, current profit **35 IRR**, and campaign simulations. B has a row-level tax configuration error. HTTP 200 indicates the batch was processed; always inspect individual product statuses. Financial Decimal values are returned as strings, avoiding JSON floating-point loss.

Optional settings: `marketplace` (default `generic`) and `locale` (`en`, `fa`, `comma`). Supported per-product fields match the UI, including cost components, tax treatment, campaign margin, maximum discount and inventory. Included fields must be supplied for every product; zero is different from missing. Missing purchase cost is always an error. Maximum input: 25 MiB and 100,000 rows; use batches for larger catalogs. HTTP 400 is an invalid request, 401 an invalid token, 413 an oversized/empty body.

No current_price column means price recommendations only: no invented current profit or campaign offers. A current price is required for non-floor recommendation rules.

## Add a marketplace later

`marketprice.integrations.MarketplaceAdapter` exposes `fetch_listings()`. An adapter returns canonical listing dictionaries with stable text SKUs, currency and current selling prices. `calculate_marketplace(adapter, seller_costs, currency="IRR", target_margin="10%")` joins merchant-supplied costs by SKU, then invokes the same calculator. Missing costs invalidate the individual product. Identity, currency and selling price cannot be overwritten by the cost dictionary; costs must already use the listing currency.

Adapter implementations must handle authorization, pagination, rate limits, retries and incomplete-response detection. Fetch all requested pages or raise an error; never silently label a partial response a complete catalog. Store vendor credentials in environment variables or a secrets manager, never in spreadsheets, responses or Git. The included test uses a fake adapter, so it demonstrates the contract, not vendor connectivity.

For Amazon, use the official [SP-API authorization guide](https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api) and [Listings Items API](https://developer-docs.amazon.com/sp-api/reference/searchlistingsitems). Seller API registration/authorization is required. Listing data alone does not supply your acquisition cost, overhead or complete tax obligations. Fee estimates are price-dependent; do not reuse a single estimate as a universal fee rule.

For Digikala, obtain the current authorized seller API documentation and credentials from the seller panel before implementing an adapter. No undocumented endpoints, scraped seller cookies or assumed official commissions are built in.


## Version 1.4 additions

Pricing settings optionally accept `omitted_costs_confirmed` (boolean, default false) and `cost_states` (object: cost field → confirmed / confirmed_zero / estimated / missing). Omitted expenses otherwise produce provisional results with `decision_ready=false`. Flexible pricing exports add `Action_List` and `Cost_Confidence` (14 sections). Existing numeric floors remain comparable; consult the confidence metadata before acting.

`POST /v1/reconcile` uses the same Bearer token and size limits. Body: `{"transactions": [...], "costs": [...], "as_of": "2026-11-01"}`. Schemas are documented in [OPERATIONS.md](OPERATIONS.md). Source-row errors are returned in `Errors`; missing data never produces a confirmed aggregate. No marketplace writes are exposed.
