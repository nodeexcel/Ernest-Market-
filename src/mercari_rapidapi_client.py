"""Mercari listing search via RapidAPI (mercari-item-search)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import requests

from src.config_loader import BuyRule
from src.ebay_client import DEFAULT_LIMIT
from src.listing import Listing
from src.settings import Settings

logger = logging.getLogger(__name__)

DEFAULT_HOST = "mercari-item-search.p.rapidapi.com"
ITEMS_PATH = "/items"
REQUEST_TIMEOUT_SECONDS = 60
MERCARI_ITEM_BASE = "https://www.mercari.com/us/item"


class MercariApiError(RuntimeError):
    """Raised when Mercari RapidAPI requests fail."""


class MercariRapidApiClient:
    """Search Mercari US listings through RapidAPI."""

    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        if not settings.rapidapi_key:
            raise MercariApiError("RAPIDAPI_KEY is required when MERCARI_ENABLED=true.")
        self._api_key = settings.rapidapi_key
        self._host = settings.rapidapi_mercari_host
        self._session = session or requests.Session()

    @property
    def _items_url(self) -> str:
        return f"https://{self._host}{ITEMS_PATH}"

    def _headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": self._host,
        }

    def _request_items(self, rule: BuyRule, page: int) -> Any:
        params: dict[str, str | int] = {
            "keyword": rule.keyword,
            "page": page,
            "saleStatus": "ON_SALE",
        }
        if rule.min_price > 0:
            params["priceLow"] = int(rule.min_price)
        params["priceHight"] = int(rule.max_price)

        response = self._session.get(
            self._items_url,
            headers=self._headers(),
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 429:
            raise MercariApiError("RapidAPI Mercari rate limit exceeded (429).")
        if response.status_code != 200:
            raise MercariApiError(
                f"Mercari search failed ({response.status_code}) for keyword {rule.keyword!r}: "
                f"{response.text[:500]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise MercariApiError("Mercari search returned non-JSON response.") from exc

    @staticmethod
    def _extract_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []

        for key in ("items", "data", "results", "itemList", "products"):
            block = payload.get(key)
            if isinstance(block, list):
                return [item for item in block if isinstance(item, dict)]
            if isinstance(block, dict):
                nested = block.get("items") or block.get("data") or block.get("results")
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
        return []

    @staticmethod
    def _first_str(item: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = item.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    @staticmethod
    def _parse_price(item: dict[str, Any]) -> float | None:
        for key in ("price", "itemPrice", "amount", "converted_price"):
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, dict):
                nested = value.get("amount") or value.get("value")
                if nested is not None:
                    value = nested
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _parse_condition(item: dict[str, Any]) -> str:
        for key in ("condition", "itemCondition", "status", "itemStatus"):
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, dict):
                name = value.get("name") or value.get("label")
                if name:
                    return str(name)
            return str(value)
        return "Unknown"

    def _parse_item(self, item: dict[str, Any], keyword: str) -> Listing | None:
        item_id = self._first_str(item, "id", "itemId", "item_id")
        title = self._first_str(item, "name", "title", "productName", "itemName")
        if not item_id or not title:
            return None

        if not item_id.startswith("m"):
            item_id = f"m{item_id}"

        price = self._parse_price(item)
        if price is None:
            return None

        url = self._first_str(item, "url", "productURL", "itemUrl", "permalink")
        if not url:
            url = f"{MERCARI_ITEM_BASE}/{item_id}/"

        status = str(item.get("status", "")).upper()
        if status in {"SOLD_OUT", "STATUS_SOLD_OUT", "SOLD"}:
            return None

        return Listing(
            item_id=item_id,
            title=title,
            price=price,
            currency="USD",
            url=url,
            condition=self._parse_condition(item),
            keyword=keyword,
            marketplace="mercari",
        )

    def search_rule(self, rule: BuyRule, max_results: int = DEFAULT_LIMIT) -> list[Listing]:
        """Fetch Mercari listings for a single buy rule."""
        listings: list[Listing] = []
        seen_ids: set[str] = set()
        page = 1
        max_pages = 3

        while len(listings) < max_results and page <= max_pages:
            payload = self._request_items(rule, page)
            raw_items = self._extract_items(payload)
            if not raw_items:
                break

            for raw_item in raw_items:
                listing = self._parse_item(raw_item, rule.keyword)
                if listing is None or listing.item_id in seen_ids:
                    continue
                seen_ids.add(listing.item_id)
                listings.append(listing)
                if len(listings) >= max_results:
                    break

            page += 1

        logger.info(
            "Mercari search for %r returned %d parsed listing(s).",
            rule.keyword,
            len(listings),
        )
        return listings

    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str:
        params = {
            "keyword": rule.keyword,
            "page": 1,
            "saleStatus": "ON_SALE",
            "priceHight": int(rule.max_price),
        }
        if rule.min_price > 0:
            params["priceLow"] = int(rule.min_price)
        return f"{self._items_url}?{urlencode(params)}"
