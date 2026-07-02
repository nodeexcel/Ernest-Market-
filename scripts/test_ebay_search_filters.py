"""Offline tests for US-only and Buy It Now search constraints."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import BuyRule
from src.ebay_search_filters import (
    build_browse_api_filter,
    build_scraper_search_url,
    title_suggests_international,
)
from src.filter import RejectReason, evaluate_listing
from src.listing import Listing


def run_tests() -> int:
    rule = BuyRule(keyword="Libre 2 sensor", max_price=27.5, min_price=5.0)
    failed = 0

    scraper_url = build_scraper_search_url(rule, max_price_tolerance_percent=10.0)
    query = parse_qs(urlparse(scraper_url).query)
    checks = [
        ("scraper LH_BIN", query.get("LH_BIN") == ["1"]),
        ("scraper LH_PrefLoc", query.get("LH_PrefLoc") == ["1"]),
        ("scraper price cap", query.get("_udhi") == ["30.25"]),
    ]
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if not ok:
            failed += 1

    browse_filter = build_browse_api_filter(rule, 30.25, us_only=True, buy_it_now_only=True)
    browse_checks = [
        ("browse price filter", "price:[5.0..30.25],priceCurrency:USD" in browse_filter),
        ("browse BIN filter", "buyingOptions:{FIXED_PRICE}" in browse_filter),
        ("browse US filter", "itemLocationCountry:US" in browse_filter),
    ]
    for name, ok in browse_checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if not ok:
            failed += 1

    if title_suggests_international("Dexcom G7 Sensors Ships from China"):
        print("[PASS] international title phrase detected")
    else:
        print("[FAIL] international title phrase not detected")
        failed += 1

    listing = Listing(
        item_id="intl-1",
        title="Freestyle Libre 2 Sensor Import Charges May Apply",
        price=20.0,
        currency="USD",
        url="https://www.ebay.com/itm/intl-1",
        condition="Brand New",
        keyword="Libre 2 sensor",
    )
    decision = evaluate_listing(listing, rule, us_listings_only=True)
    if not decision.accepted and decision.reason == RejectReason.INTERNATIONAL_LISTING:
        print("[PASS] international listing rejected in filter")
    else:
        print("[FAIL] international listing should be rejected")
        failed += 1

    print()
    if failed:
        print(f"{failed} eBay search filter test(s) failed.")
        return 1
    print("All eBay search filter tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
