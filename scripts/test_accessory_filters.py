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


def _listing(keyword: str, title: str, price: float = 25.0) -> Listing:
    return Listing(
        item_id="test-1",
        title=title,
        price=price,
        currency="USD",
        url="https://www.ebay.com/itm/test-1",
        condition="New",
        keyword=keyword,
    )


def run_tests() -> int:
    settings = load_settings()
    config = load_config(settings.config_path)
    rules_by_keyword = {rule.keyword: rule for rule in config.rules}

    accessory_titles = [
        ("Dexcom G7 sensor", "Dexcom G7 Sensor Overpatch Adhesive Patches 20 Pack"),
        ("Dexcom G7 sensor", "Dexcom G7 Sensor Silicone Case Protector Cover Black"),
        ("Dexcom G7 sensor", "Dexcom G7 Sensor Tempered Glass Screen Protector Kit"),
        ("Dexcom G6 sensors", "Dexcom G6 Sensors Skin Grip Tape Accessories Only"),
        ("Omnipod 5", "Omnipod 5 Pod Sticker Decal Skin Wrap 3 Pack"),
        ("Libre 3 sensor", "Libre 3 Sensor Silicone Band Cover Accessory"),
        ("Accu-Chek Aviva Plus 100", "Accu-Chek Aviva Plus 100 Test Strips Carrying Case Only"),
    ]

    sealed_titles = [
        ("Dexcom G7 sensor", "Dexcom G7 Sensor 3 Pack Factory Sealed New"),
        ("Omnipod 5", "Omnipod 5 Pods 10 Pack Sealed Exp 2026"),
        ("Accu-Chek Aviva Plus 100", "Accu-Chek Aviva Plus 100 Test Strips Sealed Box"),
    ]

    failed = 0

    for keyword, title in accessory_titles:
        rule = rules_by_keyword[keyword]
        decision = evaluate_listing(_listing(keyword, title, rule.max_price - 1), rule)
        ok = not decision.accepted and decision.reason == RejectReason.EXCLUDED_WORD
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] reject accessory: {title[:60]}...")
        if not ok:
            failed += 1
            print(f"       expected reject (EXCLUDED_WORD), got accepted={decision.accepted} reason={decision.reason}")

    for keyword, title in sealed_titles:
        rule = rules_by_keyword[keyword]
        decision = evaluate_listing(_listing(keyword, title, rule.max_price - 1), rule)
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
