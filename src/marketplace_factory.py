"""Factory routing buy rules to eBay or Mercari search clients."""

from __future__ import annotations

from typing import Protocol

from src.config_loader import BuyRule
from src.ebay_client import DEFAULT_LIMIT
from src.ebay_factory import create_ebay_client
from src.listing import Listing
from src.mercari_rapidapi_client import MercariRapidApiClient
from src.settings import Settings


class MarketplaceSearchClient(Protocol):
    def search_rule(self, rule: BuyRule, max_results: int = DEFAULT_LIMIT) -> list[Listing]: ...
    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str: ...


class MarketplaceRouter:
    """Dispatch search requests by rule marketplace."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ebay = create_ebay_client(settings)
        self._mercari: MercariRapidApiClient | None = None
        if settings.mercari_enabled:
            self._mercari = MercariRapidApiClient(settings)

    def search_rule(self, rule: BuyRule, max_results: int = DEFAULT_LIMIT) -> list[Listing]:
        client = self._client_for(rule.marketplace)
        return client.search_rule(rule, max_results=max_results)

    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str:
        return self._client_for(rule.marketplace).debug_search_url(rule, limit=limit)

    def _client_for(self, marketplace: str) -> MarketplaceSearchClient:
        if marketplace == "ebay":
            return self._ebay
        if marketplace == "mercari":
            if self._mercari is None:
                raise RuntimeError(
                    "Mercari is disabled. Set MERCARI_ENABLED=true and RAPIDAPI_KEY in .env."
                )
            return self._mercari
        raise RuntimeError(f"Unsupported marketplace: {marketplace!r}")


def create_marketplace_router(settings: Settings) -> MarketplaceRouter:
    return MarketplaceRouter(settings)
