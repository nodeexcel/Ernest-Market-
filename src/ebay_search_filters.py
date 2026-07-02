"""Shared eBay search constraints (US-only, Buy It Now)."""

from __future__ import annotations

from urllib.parse import urlencode

from src.config_loader import BuyRule
from src.pricing import effective_max_price

EBAY_SEARCH_BASE = "https://www.ebay.com/sch/i.html"

# Title phrases that often indicate overseas sellers or import fees.
_INTERNATIONAL_TITLE_PHRASES = frozenset(
    {
        "ships from china",
        "ship from china",
        "from china",
        "from hong kong",
        "from uk",
        "from japan",
        "from korea",
        "from singapore",
        "import charges",
        "import fee",
        "customs fee",
        "international shipping",
        "ships internationally",
        "worldwide shipping",
        "tariff",
    }
)


def title_suggests_international(title: str) -> bool:
    """Return True when the listing title hints at non-US or import-heavy shipping."""
    lowered = " ".join(title.strip().lower().split())
    if not lowered:
        return False
    return any(phrase in lowered for phrase in _INTERNATIONAL_TITLE_PHRASES)


def build_price_filter(rule: BuyRule, price_cap: float) -> str:
    """Browse API price filter fragment."""
    if rule.min_price > 0:
        return f"price:[{rule.min_price}..{price_cap}],priceCurrency:USD"
    return f"price:[..{price_cap}],priceCurrency:USD"


def build_browse_api_filter(
    rule: BuyRule,
    price_cap: float,
    *,
    us_only: bool = True,
    buy_it_now_only: bool = True,
) -> str:
    """Combine Browse API filters for price, location, and buying format."""
    parts = [build_price_filter(rule, price_cap)]
    if buy_it_now_only:
        parts.append("buyingOptions:{FIXED_PRICE}")
    if us_only:
        parts.append("itemLocationCountry:US")
    return ",".join(parts)


def build_scraper_search_params(
    rule: BuyRule,
    *,
    max_price_tolerance_percent: float = 0.0,
    us_only: bool = True,
    buy_it_now_only: bool = True,
) -> dict[str, str | float | int]:
    """eBay HTML search URL query parameters."""
    price_cap = effective_max_price(rule.max_price, max_price_tolerance_percent)
    params: dict[str, str | float | int] = {
        "_nkw": rule.keyword,
        "_sacat": 0,
        "_udhi": price_cap,
    }
    if rule.min_price > 0:
        params["_udlo"] = rule.min_price
    if buy_it_now_only:
        params["LH_BIN"] = 1
    if us_only:
        params["LH_PrefLoc"] = 1
    return params


def build_scraper_search_url(
    rule: BuyRule,
    *,
    max_price_tolerance_percent: float = 0.0,
    us_only: bool = True,
    buy_it_now_only: bool = True,
) -> str:
    """Full eBay search URL for ScraperAPI."""
    params = build_scraper_search_params(
        rule,
        max_price_tolerance_percent=max_price_tolerance_percent,
        us_only=us_only,
        buy_it_now_only=buy_it_now_only,
    )
    return f"{EBAY_SEARCH_BASE}?{urlencode(params)}"
