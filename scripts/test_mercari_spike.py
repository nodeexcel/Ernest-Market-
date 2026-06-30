"""Spike test: verify ScraperAPI can fetch and parse Mercari search HTML.

Run before implementing Mercari Phase 2. Does not send alerts or modify state.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup

from src.scraperapi_fetch import ScraperApiError, fetch_html
from src.settings import SettingsError, load_ebay_settings

MERCARI_SEARCH_BASE = "https://www.mercari.com/search/"
ITEM_PATH_RE = re.compile(r"/(?:us/)?item/[a-z]?\d+", re.IGNORECASE)
PRICE_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")


@dataclass(frozen=True)
class MercariSpikeItem:
    title: str
    price_text: str
    url: str


def build_mercari_search_url(keyword: str) -> str:
    return f"{MERCARI_SEARCH_BASE}?{urlencode({'keyword': keyword})}"


def _normalize_url(href: str) -> str | None:
    href = href.strip()
    if not href:
        return None
    if href.startswith("/"):
        return f"https://www.mercari.com{href.split('?')[0]}"
    if href.startswith("http") and "mercari.com" in href:
        return href.split("?")[0]
    return None


def _extract_title(anchor: object) -> str:
    text = anchor.get_text(" ", strip=True) if hasattr(anchor, "get_text") else ""
    if text:
        return text[:200]
    aria = anchor.get("aria-label", "") if hasattr(anchor, "get") else ""
    return str(aria).strip()[:200]


def parse_mercari_listings(html: str, *, max_results: int = 10) -> list[MercariSpikeItem]:
    """Best-effort parse of Mercari search HTML (selectors may change)."""
    soup = BeautifulSoup(html, "html.parser")
    listings: list[MercariSpikeItem] = []
    seen_urls: set[str] = set()

    anchors = soup.select('a[href*="/item/"]')
    for anchor in anchors:
        if len(listings) >= max_results:
            break

        href = str(anchor.get("href", ""))
        if not ITEM_PATH_RE.search(href):
            continue

        url = _normalize_url(href)
        if not url or url in seen_urls:
            continue

        title = _extract_title(anchor)
        if not title or len(title) < 3:
            continue

        container = anchor.find_parent(["div", "li", "article"])
        price_text = ""
        if container:
            container_text = container.get_text(" ", strip=True)
            match = PRICE_RE.search(container_text)
            if match:
                price_text = match.group(0)

        seen_urls.add(url)
        listings.append(MercariSpikeItem(title=title, price_text=price_text or "?", url=url))

    return listings


def _detect_block_page(html: str) -> str | None:
    lowered = html.lower()
    markers = (
        "access denied",
        "captcha",
        "verify you are human",
        "unusual traffic",
        "enable javascript",
    )
    for marker in markers:
        if marker in lowered:
            return marker
    return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test ScraperAPI + Mercari search HTML before Phase 2 integration.",
    )
    parser.add_argument(
        "--keyword",
        default="dexcom",
        help="Mercari search keyword (default: dexcom).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max listings to print (default: 5).",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Enable ScraperAPI JavaScript rendering (slower, uses more credits).",
    )
    parser.add_argument(
        "--premium",
        action="store_true",
        help="Enable ScraperAPI premium proxies (required for protected sites like Mercari).",
    )
    parser.add_argument(
        "--save-html",
        action="store_true",
        help="Save raw HTML to data/mercari_spike_sample.html for debugging.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        settings = load_ebay_settings()
    except SettingsError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    if settings.ebay_backend != "scraperapi" or not settings.scraperapi_key:
        print(
            "Mercari spike requires ScraperAPI. Set EBAY_BACKEND=scraperapi and SCRAPERAPI_KEY in .env.",
            file=sys.stderr,
        )
        return 1

    target_url = build_mercari_search_url(args.keyword)
    print(f"Mercari search URL: {target_url}")
    print(f"ScraperAPI render={args.render}, premium={args.premium}")
    print()

    try:
        html = fetch_html(
            settings.scraperapi_key,
            target_url,
            render=args.render,
            premium=args.premium,
        )
    except ScraperApiError as exc:
        error_text = str(exc)
        needs_ultra = "ultra_premium=true" in error_text.lower()
        if args.premium and needs_ultra:
            print("WARN: ScraperAPI requires ultra_premium for this Mercari request; retrying...")
            try:
                html = fetch_html(
                    settings.scraperapi_key,
                    target_url,
                    render=args.render,
                    premium=args.premium,
                    ultra_premium=True,
                )
            except ScraperApiError as retry_exc:
                print(f"FAIL: {retry_exc}", file=sys.stderr)
                return 1
        else:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1

    print(f"HTML received: {len(html):,} bytes")

    block = _detect_block_page(html)
    if block:
        print(f"WARN: Page may be blocked or incomplete (matched: {block!r}).")
        print("Try again with --render if you have not already.")

    if args.save_html:
        out_path = settings.data_dir / "mercari_spike_sample.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        print(f"Saved HTML to {out_path}")

    listings = parse_mercari_listings(html, max_results=args.limit)
    print(f"Parsed listings: {len(listings)}")
    print()

    if not listings:
        print("FAIL: No Mercari items parsed from HTML.")
        print("Next steps:")
        print("  1. Re-run with --premium --render --save-html")
        print("  2. Inspect data/mercari_spike_sample.html for item link patterns")
        print("  3. If still blocked, consider RapidAPI Mercari or Playwright fallback")
        return 1

    for index, item in enumerate(listings, start=1):
        print(f"{index}. {item.price_text} — {item.title}")
        print(f"   {item.url}")
        print()

    print("PASS: ScraperAPI returned parseable Mercari search results.")
    print("Safe to proceed with Mercari client implementation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
