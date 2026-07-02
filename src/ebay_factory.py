"""Factory for eBay listing search clients (official API or ScraperAPI)."""

from __future__ import annotations

from typing import Protocol

from src.config_loader import BuyRule
from src.ebay_auth import EbayAuthClient
from src.ebay_client import DEFAULT_LIMIT, EbayClient, Listing
from src.ebay_scraper_client import EbayScraperClient
from src.settings import EbaySettings


class EbaySearchClient(Protocol):
    def search_rule(self, rule: BuyRule, max_results: int = DEFAULT_LIMIT) -> list[Listing]: ...
    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str: ...


def create_ebay_client(settings: EbaySettings) -> EbaySearchClient:
    """Return the configured eBay search backend."""
    if settings.ebay_backend == "scraperapi":
        return EbayScraperClient(
            scraperapi_key=settings.scraperapi_key or "",
            us_only=settings.ebay_us_only,
            buy_it_now_only=settings.ebay_buy_it_now_only,
        )
    auth = EbayAuthClient(settings)
    return EbayClient(settings, auth)
