"""eBay listing search via ScraperAPI (HTML scraping for testing)."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from src.config_loader import BuyRule
from src.ebay_client import DEFAULT_LIMIT
from src.listing import Listing
from src.scraperapi_fetch import ScraperApiError, fetch_html

logger = logging.getLogger(__name__)

SCRAPERAPI_ENDPOINT = "https://api.scraperapi.com"
EBAY_SEARCH_BASE = "https://www.ebay.com/sch/i.html"
REQUEST_TIMEOUT_SECONDS = 90


class EbayScraperError(RuntimeError):
    """Raised when ScraperAPI or HTML parsing fails."""


class EbayScraperClient:
    """Fetch eBay search results through ScraperAPI and parse listing HTML."""

    def __init__(
        self,
        scraperapi_key: str,
        session: requests.Session | None = None,
    ) -> None:
        if not scraperapi_key.strip():
            raise EbayScraperError("SCRAPERAPI_KEY is required when EBAY_BACKEND=scraperapi.")
        self._api_key = scraperapi_key.strip()
        self._session = session or requests.Session()

    @staticmethod
    def build_ebay_search_url(rule: BuyRule) -> str:
        params: dict[str, str | float | int] = {
            "_nkw": rule.keyword,
            "_sacat": 0,
            "_udhi": rule.max_price,
        }
        if rule.min_price > 0:
            params["_udlo"] = rule.min_price
        return f"{EBAY_SEARCH_BASE}?{urlencode(params)}"

    def _fetch_html(self, target_url: str) -> str:
        try:
            return fetch_html(
                self._api_key,
                target_url,
                session=self._session,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except ScraperApiError as exc:
            raise EbayScraperError(str(exc)) from exc

    @staticmethod
    def _parse_price(raw_price: str) -> float | None:
        cleaned = raw_price.replace(",", "").strip()
        match = re.search(r"([\d]+(?:\.\d+)?)", cleaned)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    @staticmethod
    def _extract_item_id(url: str) -> str | None:
        match = re.search(r"/itm/(?:[^/]+/)?(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"[?&]itm=(\d+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _is_placeholder_title(title: str) -> bool:
        lowered = title.strip().lower()
        return lowered in {"shop on ebay", "new listing"} or not lowered

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = title.strip()
        if cleaned.lower().startswith("new listing"):
            cleaned = cleaned[11:].strip()
        for suffix in ("Opens in a new window", "Opens in new window"):
            if suffix.lower() in cleaned.lower():
                cleaned = cleaned.split(suffix)[0].strip()
        return cleaned

    def _parse_listings(self, html: str, keyword: str, max_results: int) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings: list[Listing] = []
        seen_ids: set[str] = set()

        items = soup.select(".srp-results li.s-card")
        if not items:
            items = soup.select("li.s-item")
        if not items:
            items = soup.select('[class*="s-item"]')

        for item in items:
            if len(listings) >= max_results:
                break

            title_el = (
                item.select_one(".s-card__title")
                or item.select_one(".s-item__title")
                or item.select_one('[class*="s-card__title"]')
                or item.select_one('[class*="s-item__title"]')
                or item.select_one("h3")
            )
            price_el = (
                item.select_one(".s-card__price")
                or item.select_one(".s-item__price")
                or item.select_one('[class*="s-card__price"]')
                or item.select_one('[class*="s-item__price"]')
            )
            link_el = (
                item.select_one('a[href*="/itm/"]')
                or item.select_one("a.s-item__link")
                or item.select_one("a.s-card__link")
            )

            if not title_el or not price_el or not link_el:
                continue

            title = self._clean_title(title_el.get_text(strip=True))
            if self._is_placeholder_title(title):
                continue

            price = self._parse_price(price_el.get_text(strip=True))
            if price is None:
                continue

            url = str(link_el.get("href", "")).split("?")[0]
            if not url.startswith("http"):
                continue

            item_id = self._extract_item_id(url)
            if not item_id or item_id in seen_ids:
                continue

            subtitle_el = (
                item.select_one(".s-item__subtitle")
                or item.select_one('[class*="s-item__subtitle"]')
                or item.select_one(".s-card__subtitle")
            )
            condition = subtitle_el.get_text(strip=True) if subtitle_el else "Unknown"

            seen_ids.add(item_id)
            listings.append(
                Listing(
                    item_id=item_id,
                    title=title,
                    price=price,
                    currency="USD",
                    url=url,
                    condition=condition,
                    keyword=keyword,
                    marketplace="ebay",
                )
            )

        return listings

    def search_rule(self, rule: BuyRule, max_results: int = DEFAULT_LIMIT) -> list[Listing]:
        """Fetch and parse eBay listings for a buy rule via ScraperAPI."""
        target_url = self.build_ebay_search_url(rule)
        logger.info("ScraperAPI fetching eBay search for keyword=%r", rule.keyword)
        html = self._fetch_html(target_url)
        listings = self._parse_listings(html, rule.keyword, max_results)
        logger.info(
            "ScraperAPI search for %r returned %d parsed listing(s).",
            rule.keyword,
            len(listings),
        )
        return listings

    def debug_search_url(self, rule: BuyRule, limit: int = 10) -> str:
        return self.build_ebay_search_url(rule)
