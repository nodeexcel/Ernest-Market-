"""CLI helper to verify Mercari RapidAPI search connectivity."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import BuyRule, load_config
from src.logging_setup import configure_logging
from src.mercari_rapidapi_client import MercariRapidApiClient
from src.settings import SettingsError, load_settings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test Mercari RapidAPI search for Ernest Market.")
    parser.add_argument("--keyword", help="Override keyword (uses first mercari rule if omitted).")
    parser.add_argument("--max-price", type=float, help="Override max price for test search.")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to fetch.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        settings = load_settings()
    except SettingsError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    if not settings.mercari_enabled:
        print("Set MERCARI_ENABLED=true and RAPIDAPI_KEY in .env first.", file=sys.stderr)
        return 1

    configure_logging(settings)
    logger = logging.getLogger(__name__)

    try:
        config = load_config(settings.config_path, mirror_mercari=True)
    except Exception as exc:
        logger.error("Config error: %s", exc)
        return 1

    if args.keyword:
        max_price = args.max_price if args.max_price is not None else 100.0
        rule = BuyRule(keyword=args.keyword, max_price=max_price, marketplace="mercari")
    else:
        mercari_rules = [rule for rule in config.rules if rule.marketplace == "mercari"]
        if not mercari_rules:
            print("No mercari rules in config.", file=sys.stderr)
            return 1
        rule = mercari_rules[0]
        if args.max_price is not None:
            rule = BuyRule(
                keyword=rule.keyword,
                max_price=args.max_price,
                min_price=rule.min_price,
                match_in=rule.match_in,
                exclude_words=rule.exclude_words,
                marketplace="mercari",
            )

    client = MercariRapidApiClient(settings)

    print("Backend: rapidapi (mercari-item-search)")
    print(f"Testing Mercari search — keyword={rule.keyword!r}, max_price={rule.max_price}")
    print(f"Search URL: {client.debug_search_url(rule, limit=args.limit)}")
    print()

    try:
        listings = client.search_rule(rule, max_results=args.limit)
    except Exception as exc:
        logger.exception("Mercari test failed.")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not listings:
        print("No listings returned.")
        return 1

    for index, listing in enumerate(listings, start=1):
        print(f"{index}. ${listing.price:.2f} — {listing.title}")
        print(f"   {listing.url}")
        print()

    print("PASS: Mercari RapidAPI returned listings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
