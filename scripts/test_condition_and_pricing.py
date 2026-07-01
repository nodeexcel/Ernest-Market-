"""Offline tests for condition rejection and +10% price tolerance."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import load_config
from src.filter import RejectReason, evaluate_listing
from src.listing import Listing
from src.pricing import effective_max_price
from src.settings import load_settings


def _listing(
    keyword: str,
    title: str,
    *,
    price: float,
    condition: str = "Brand New",
) -> Listing:
    return Listing(
        item_id="test-item",
        title=title,
        price=price,
        currency="USD",
        url="https://www.ebay.com/itm/test-item",
        condition=condition,
        keyword=keyword,
    )


def run_tests() -> int:
    settings = load_settings()
    config = load_config(settings.config_path)
    rules_by_keyword = {rule.keyword: rule for rule in config.rules}
    tolerance = settings.max_price_tolerance_percent
    libre_rule = rules_by_keyword["Libre 2 sensor"]
    meter_rule = rules_by_keyword["glucose meter"]
    cap = effective_max_price(libre_rule.max_price, tolerance)
    failed = 0

    if cap != 30.25:
        print(f"[FAIL] effective max price expected 30.25, got {cap}")
        failed += 1
    else:
        print("[PASS] effective max price applies 10% buffer")

    cases: list[tuple[str, str, Listing, bool, RejectReason | None]] = [
        (
            "reject sensor covers accessory",
            "Libre 2 sensor",
            _listing(
                "Libre 2 sensor",
                "24 PCS Sensor Covers for Libre 2 Waterproof",
                price=13.0,
            ),
            False,
            RejectReason.EXCLUDED_WORD,
        ),
        (
            "reject decal sticker",
            "Libre 2 sensor",
            _listing(
                "Libre 2 sensor",
                "Decal Sticker for Freestyle Libre 2 Sensor",
                price=10.0,
            ),
            False,
            RejectReason.EXCLUDED_WORD,
        ),
        (
            "reject open box condition",
            "glucose meter",
            _listing(
                "glucose meter",
                "One Touch Ultra 2 Glucose Meter",
                price=6.0,
                condition="Open Box",
            ),
            False,
            RejectReason.BAD_CONDITION,
        ),
        (
            "reject pre-owned condition",
            "glucose meter",
            _listing(
                "glucose meter",
                "Bayer Contour Glucose Meter",
                price=6.0,
                condition="Pre-Owned",
            ),
            False,
            RejectReason.BAD_CONDITION,
        ),
        (
            "accept brand new sealed listing",
            "Libre 2 sensor",
            _listing(
                "Libre 2 sensor",
                "Freestyle Libre 2 Sensor 2 Pack Sealed",
                price=25.0,
                condition="Brand New",
            ),
            True,
            None,
        ),
        (
            "accept price within 10% above list",
            "Libre 2 sensor",
            _listing(
                "Libre 2 sensor",
                "Freestyle Libre 2 Sensor Sealed Box",
                price=30.0,
                condition="Brand New",
            ),
            True,
            None,
        ),
        (
            "reject price above 10% buffer",
            "Libre 2 sensor",
            _listing(
                "Libre 2 sensor",
                "Freestyle Libre 2 Sensor Sealed Box",
                price=31.0,
                condition="Brand New",
            ),
            False,
            RejectReason.PRICE_TOO_HIGH,
        ),
    ]

    for name, keyword, listing, expected_accept, expected_reason in cases:
        rule = libre_rule if keyword == "Libre 2 sensor" else meter_rule
        decision = evaluate_listing(
            listing,
            rule,
            max_price_tolerance_percent=tolerance,
        )
        ok = decision.accepted == expected_accept and decision.reason == expected_reason
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if not ok:
            failed += 1
            print(
                f"       expected accepted={expected_accept} reason={expected_reason}, "
                f"got accepted={decision.accepted} reason={decision.reason}"
            )

    print()
    if failed:
        print(f"{failed} condition/pricing test(s) failed.")
        return 1
    print("All condition and pricing tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
