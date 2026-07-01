"""Verify accessory listings are rejected for medical buy rules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import load_config
from src.filter import RejectReason, evaluate_listing
from src.listing import Listing
from src.settings import load_settings


def _listing(
    keyword: str,
    title: str,
    *,
    price: float,
    condition: str = "Brand New",
) -> Listing:
    return Listing(
        item_id="test-1",
        title=title,
        price=price,
        currency="USD",
        url="https://www.ebay.com/itm/test-1",
        condition=condition,
        keyword=keyword,
    )


def run_tests() -> int:
    settings = load_settings()
    config = load_config(settings.config_path)
    rules_by_keyword = {rule.keyword: rule for rule in config.rules}
    tolerance = settings.max_price_tolerance_percent

    accessory_titles = [
        ("Dexcom G7 sensor", "Dexcom G7 Sensor Overpatch Adhesive Patches 20 Pack", 30.0),
        ("Dexcom G7 sensor", "Dexcom G7 Sensor Silicone Case Protector Cover Black", 30.0),
        ("Dexcom G7 sensor", "Dexcom G7 Sensor Tempered Glass Screen Protector Kit", 30.0),
        ("Dexcom G6 sensors", "Dexcom G6 Sensors Skin Grip Tape Accessories Only", 100.0),
        ("Omnipod 5", "Omnipod 5 Pod Sticker Decal Skin Wrap 3 Pack", 100.0),
        ("Libre 2 sensor", "24 PCS Sensor Covers for Libre 2 Waterproof Sweatproof", 13.0),
        ("Libre 2 sensor", "Decal Sticker for Freestyle Libre 2 Sensor Pack", 10.0),
        ("Libre 3 sensor", "Libre 3 Sensor Silicone Band Cover Accessory", 25.0),
        ("Accu-Chek Aviva Plus 100", "Accu-Chek Aviva Plus 100 Test Strips Carrying Case Only", 30.0),
        ("glucose meter", "One Touch Ultra 2 Glucose Meter", 6.0, "Open Box"),
        ("glucose meter", "Bayer Contour Glucose Meter Kit", 6.0, "Pre-Owned"),
    ]

    sealed_titles = [
        ("Dexcom G7 sensor", "Dexcom G7 Sensor 3 Pack Factory Sealed New", 35.0),
        ("Omnipod 5", "Omnipod 5 Pods 10 Pack Sealed Exp 2026", 110.0),
        ("Accu-Chek Aviva Plus 100", "Accu-Chek Aviva Plus 100 Test Strips Sealed Box", 31.0),
        ("Libre 2 sensor", "Freestyle Libre 2 Sensor 2 Pack Sealed New", 29.0),
    ]

    failed = 0

    for entry in accessory_titles:
        if len(entry) == 4:
            keyword, title, price, condition = entry
        else:
            keyword, title, price = entry
            condition = "Brand New"
        rule = rules_by_keyword[keyword]
        decision = evaluate_listing(
            _listing(keyword, title, price=price, condition=condition),
            rule,
            max_price_tolerance_percent=tolerance,
        )
        ok = not decision.accepted and decision.reason in {
            RejectReason.EXCLUDED_WORD,
            RejectReason.BAD_CONDITION,
        }
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] reject bad listing: {title[:60]}...")
        if not ok:
            failed += 1
            print(f"       expected reject, got accepted={decision.accepted} reason={decision.reason}")

    for keyword, title, price in sealed_titles:
        rule = rules_by_keyword[keyword]
        decision = evaluate_listing(
            _listing(keyword, title, price=price),
            rule,
            max_price_tolerance_percent=tolerance,
        )
        ok = decision.accepted
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] accept sealed box: {title[:60]}...")
        if not ok:
            failed += 1
            print(f"       expected accept, got reason={decision.reason}")

    print()
    if failed:
        print(f"{failed} accessory filter test(s) failed.")
        return 1
    print("All accessory filter tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
