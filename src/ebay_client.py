"""eBay Browse API client for listing search."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import requests

from src.config_loader import BuyRule
from src.ebay_auth import EbayAuthClient, EbayAuthError
from src.ebay_search_filters import build_browse_api_filter
from src.listing import Listing
from src.pricing import effective_max_price
from src.settings import EbaySettings

logger = logging.getLogger(__name__)

SEARCH_ENDPOINT = "/buy/browse/v1/item_summary/search"
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class EbayApiError(RuntimeError):
    """Raised when eBay Browse API requests fail."""


class EbayClient:
    """Search eBay listings via the official Browse API."""

    def __init__(
        self,
        settings: EbaySettings,
        auth_client: EbayAuthClient,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings
        self._auth = auth_client
        self._session = session or requests.Session()

    @property
    def _search_url(self) -> str:
        return f"{self._settings.ebay_api_base}{SEARCH_ENDPOINT}"

    def _headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": self._settings.ebay_marketplace_id,
        }

    def _build_search_filter(self, rule: BuyRule, price_cap: float) -> str:
        return build_browse_api_filter(
            rule,
            price_cap,
            us_only=self._settings.ebay_us_only,
            buy_it_now_only=self._settings.ebay_buy_it_now_only,
        )

    def _build_params(
        self,
        rule: BuyRule,
        limit: int,
        offset: int,
        *,
        price_cap: float,
    ) -> dict[str, str | int]:
        return {
            "q": rule.keyword,
            "limit": limit,
            "offset": offset,
            "filter": self._build_search_filter(rule, price_cap),
        }

    def _request_search(
        self,
        access_token: str,
        rule: BuyRule,
        limit: int,
        offset: int,
        *,
        price_cap: float,
    ) -> dict[str, Any]:
        params = self._build_params(rule, limit, offset, price_cap=price_cap)
        response = self._session.get(
            self._search_url,
            headers=self._headers(access_token),
            params=params,
            timeout=30,
        )

        if response.status_code == 401:
            raise EbayAuthError("eBay access token rejected (401).")
        if response.status_code == 429:
            raise EbayApiError("eBay rate limit exceeded (429). Try again later.")
        if response.status_code != 200:
            raise EbayApiError(
                f"eBay search failed ({response.status_code}) for keyword {rule.keyword!r}: "
                f"{response.text[:500]}"
            )

        payload = response.json()
        if not isinstance(payload, dict):
            raise EbayApiError("eBay search returned a non-object JSON payload.")
        return payload

    @staticmethod
    def _parse_item(item: dict[str, Any], keyword: str) -> Listing | None:
        item_id = item.get("itemId")
        title = item.get("title")
        price_block = item.get("price") or {}
        value = price_block.get("value")
        currency = price_block.get("currency", "USD")

        if not item_id or not title:
            return None

        try:
            price = float(value)
        except (TypeError, ValueError):
            logger.debug("Skipping item %s — missing or invalid price.", item_id)
            return None

        url = item.get("itemWebUrl") or f"https://www.ebay.com/itm/{item_id}"
        condition = item.get("condition") or item.get("conditionId") or "Unknown"

        return Listing(
            item_id=str(item_id),
            title=str(title),
            price=price,
            currency=str(currency),
            url=str(url),
            condition=str(condition),
            keyword=keyword,
            marketplace="ebay",
        )

    def search_rule(
        self,
        rule: BuyRule,
        max_results: int = DEFAULT_LIMIT,
        *,
        max_price_tolerance_percent: float = 0.0,
    ) -> list[Listing]:
        """Fetch listings for a single buy rule."""
        listings: list[Listing] = []
        offset = 0
        limit = min(max_results, MAX_LIMIT)
        price_cap = effective_max_price(rule.max_price, max_price_tolerance_percent)
        access_token = self._auth.get_access_token()
        retried_auth = False

        while len(listings) < max_results:
            try:
                payload = self._request_search(
                    access_token,
                    rule,
                    limit,
                    offset,
                    price_cap=price_cap,
                )
            except EbayAuthError:
                if retried_auth:
                    raise
                logger.warning("eBay token expired during search; refreshing.")
                self._auth.invalidate()
                access_token = self._auth.get_access_token(force_refresh=True)
                retried_auth = True
                continue

            summaries = payload.get("itemSummaries") or []
            if not summaries:
                break

            for raw_item in summaries:
                if not isinstance(raw_item, dict):
                    continue
                listing = self._parse_item(raw_item, rule.keyword)
                if listing is not None:
                    listings.append(listing)
                if len(listings) >= max_results:
                    break

            total = payload.get("total")
            offset += len(summaries)
            if len(summaries) < limit:
                break
            if isinstance(total, int) and offset >= total:
                break

        logger.info(
            "eBay search for %r returned %d parsed listing(s).",
            rule.keyword,
            len(listings),
        )
        return listings

    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str:
        """Return a human-readable search URL for manual debugging."""
        params = self._build_params(rule, limit=limit, offset=0, price_cap=rule.max_price)
        return f"{self._search_url}?{urlencode(params)}"
