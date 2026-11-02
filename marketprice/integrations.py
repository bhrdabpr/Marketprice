"""Marketplace adapter contract: read listings, join seller costs, calculate locally.

No live vendor connector is installed. Implement the protocol using an authorized
seller API, with its pagination, retries and credential handling outside the engine.
"""

from typing import Protocol

from .flexible import calculate_catalog
from .io import MAX_ROWS


class MarketplaceAdapter(Protocol):
    def fetch_listings(self) -> list[dict]:
        """Return canonical fields (sku, currency, current_price, etc.), never invented costs."""
        ...


def calculate_marketplace(adapter: MarketplaceAdapter, seller_costs: dict[str, dict], **settings):
    listings = adapter.fetch_listings()
    if not listings or len(listings) > MAX_ROWS:
        raise ValueError("Adapter must return 1 to 100000 listings; paginate upstream")
    rows = []
    for listing in listings:
        sku = listing.get("sku")
        if not isinstance(sku, str) or not sku.strip():
            raise ValueError("Marketplace listings require stable text SKUs")
        costs = seller_costs.get(sku, {})
        if any(k in costs for k in ("sku", "currency", "current_price", "marketplace")):
            raise ValueError("Seller costs must not overwrite marketplace identity, currency or price")
        rows.append({**listing, **costs})
    return calculate_catalog(rows, **settings)
