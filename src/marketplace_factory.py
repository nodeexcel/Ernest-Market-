"""Factory routing buy rules to the eBay search client."""

from __future__ import annotations

from typing import Protocol

from src.config_loader import BuyRule
from src.ebay_client import DEFAULT_LIMIT
from src.ebay_factory import create_ebay_client
from src.listing import Listing
from src.settings import Settings


class MarketplaceSearchClient(Protocol):
    def search_rule(self, rule: BuyRule, max_results: int = DEFAULT_LIMIT) -> list[Listing]: ...
    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str: ...


class MarketplaceRouter:
    """Dispatch search requests to eBay."""

    def __init__(self, settings: Settings) -> None:
        self._ebay = create_ebay_client(settings)

    def search_rule(self, rule: BuyRule, max_results: int = DEFAULT_LIMIT) -> list[Listing]:
        if rule.marketplace != "ebay":
            raise RuntimeError(
                f"Unsupported marketplace {rule.marketplace!r}. This project only supports eBay."
            )
        return self._ebay.search_rule(rule, max_results=max_results)

    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str:
        return self._ebay.debug_search_url(rule, limit=limit)


def create_marketplace_router(settings: Settings) -> MarketplaceRouter:
    return MarketplaceRouter(settings)
