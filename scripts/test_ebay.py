"""CLI helper to verify eBay search connectivity (official API or ScraperAPI)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import BuyRule, load_config
from src.ebay_factory import create_ebay_client
from src.logging_setup import configure_logging
from src.settings import SettingsError, load_ebay_settings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test eBay search for Ernest Market.")
    parser.add_argument("--keyword", help="Override keyword (uses first config rule if omitted).")
    parser.add_argument("--max-price", type=float, help="Override max price for test search.")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to fetch.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        settings = load_ebay_settings()
    except SettingsError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    configure_logging(settings)
    logger = logging.getLogger(__name__)

    try:
        config = load_config(settings.config_path)
    except Exception as exc:
        logger.error("Config error: %s", exc)
        return 1

    if args.keyword:
        max_price = args.max_price if args.max_price is not None else 100.0
        rule = BuyRule(keyword=args.keyword, max_price=max_price)
    else:
        rule = config.rules[0]
        if args.max_price is not None:
            rule = BuyRule(
                keyword=rule.keyword,
                max_price=args.max_price,
                min_price=rule.min_price,
                match_in=rule.match_in,
                exclude_words=rule.exclude_words,
            )

    client = create_ebay_client(settings)
    backend = settings.ebay_backend

    print(f"Backend: {backend}")
    print(f"Testing eBay search — keyword={rule.keyword!r}, max_price={rule.max_price}")
    print(f"Search URL: {client.debug_search_url(rule, limit=args.limit)}")
    print()

    try:
        listings = client.search_rule(rule, max_results=args.limit)
    except Exception as exc:
        logger.exception("eBay test failed.")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not listings:
        print("No listings returned.")
        return 0

    for index, listing in enumerate(listings, start=1):
        print(f"{index}. ${listing.price:.2f} — {listing.title}")
        print(f"   {listing.url}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
