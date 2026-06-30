"""Offline tests for filter logic (no API keys required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import BuyRule
from src.ebay_client import Listing
from src.filter import RejectReason, evaluate_listing, filter_listings, matches_rule


def _listing(
    item_id: str,
    title: str,
    price: float = 50.0,
    keyword: str = "vintage camera",
) -> Listing:
    return Listing(
        item_id=item_id,
        title=title,
        price=price,
        currency="USD",
        url=f"https://www.ebay.com/itm/{item_id}",
        condition="Used",
        keyword=keyword,
    )


def run_tests() -> int:
    rule = BuyRule(
        keyword="vintage camera",
        max_price=75,
        min_price=10,
        exclude_words=["broken", "for parts"],
    )

    cases: list[tuple[str, Listing, bool, RejectReason | None]] = [
        (
            "accepts in-range match",
            _listing("1", "Canon AE-1 Vintage Camera Body"),
            True,
            None,
        ),
        (
            "rejects above max price",
            _listing("2", "Vintage Camera Leica M3", 200.0),
            False,
            RejectReason.PRICE_TOO_HIGH,
        ),
        (
            "rejects below min price",
            _listing("3", "Vintage Camera Film", 5.0),
            False,
            RejectReason.PRICE_TOO_LOW,
        ),
        (
            "rejects exclude word",
            _listing("4", "Vintage Camera broken lens", 50.0),
            False,
            RejectReason.EXCLUDED_WORD,
        ),
        (
            "rejects missing keyword in title",
            _listing("5", "Canon AE-1 35mm Film Body", 50.0),
            False,
            RejectReason.KEYWORD_MISMATCH,
        ),
    ]

    failed = 0
    for name, listing, expected_accept, expected_reason in cases:
        decision = evaluate_listing(listing, rule)
        ok = decision.accepted == expected_accept and decision.reason == expected_reason
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if not ok:
            failed += 1
            print(f"       expected accepted={expected_accept} reason={expected_reason}")
            print(f"       got      accepted={decision.accepted} reason={decision.reason}")

    multi_rule = BuyRule(keyword="lego star wars", max_price=40, min_price=5)
    multi_listing = _listing("6", "LEGO Star Wars X-Wing Set", 35.0, keyword="lego star wars")
    if matches_rule(multi_listing, multi_rule):
        print("[PASS] multi-word keyword match")
    else:
        print("[FAIL] multi-word keyword match")
        failed += 1

    batch = [case[1] for case in cases] + [multi_listing]
    filtered = filter_listings(batch, rule)
    if len(filtered) == 1 and filtered[0].item_id == "1":
        print("[PASS] batch filter returns only valid listing")
    else:
        print(f"[FAIL] batch filter expected 1 result, got {len(filtered)}")
        failed += 1

    print()
    if failed:
        print(f"{failed} test(s) failed.")
        return 1
    print("All filter tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
