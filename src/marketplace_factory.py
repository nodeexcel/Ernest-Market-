"""Factory routing buy rules to the eBay search client."""

from __future__ import annotations

from typing import Protocol

from src.config_loader import BuyRule
from src.ebay_factory import create_ebay_client
from src.listing import Listing
from src.settings import Settings


class MarketplaceSearchClient(Protocol):
    def search_rule(self, rule: BuyRule, max_results: int | None = None) -> list[Listing]: ...
    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str: ...


class MarketplaceRouter:
    """Dispatch search requests to eBay."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ebay = create_ebay_client(settings)

    def search_rule(self, rule: BuyRule, max_results: int | None = None) -> list[Listing]:
        if rule.marketplace != "ebay":
            raise RuntimeError(
                f"Unsupported marketplace {rule.marketplace!r}. This project only supports eBay."
            )
        resolved_limit = (
            max_results
            if max_results is not None
            else self._settings.ebay_search_default_limit
        )
        return self._ebay.search_rule(
            rule,
            max_results=resolved_limit,
            max_price_tolerance_percent=self._settings.max_price_tolerance_percent,
        )

    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str:
        return self._ebay.debug_search_url(rule, limit=limit)


def create_marketplace_router(settings: Settings) -> MarketplaceRouter:
    return MarketplaceRouter(settings)
