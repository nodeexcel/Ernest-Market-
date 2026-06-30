"""Offline tests for Mercari RapidAPI response parsing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mercari_rapidapi_client import MercariRapidApiClient


def test_extract_list_from_items_key() -> None:
    payload = {
        "items": [
            {
                "id": "m12345678901",
                "name": "Dexcom G7 Sensor 3 Pack",
                "price": 24.99,
                "status": "ON_SALE",
                "itemCondition": "New",
            }
        ]
    }
    items = MercariRapidApiClient._extract_items(payload)
    assert len(items) == 1


def test_parse_item_builds_listing() -> None:
    client = object.__new__(MercariRapidApiClient)
    listing = client._parse_item(
        {
            "id": "m12345678901",
            "name": "Dexcom G7 Sensor 3 Pack",
            "price": 24.99,
            "status": "ON_SALE",
            "itemCondition": "New",
        },
        "dexcom g7",
    )
    assert listing is not None
    assert listing.marketplace == "mercari"
    assert listing.item_id == "m12345678901"
    assert listing.dedupe_key == "mercari:m12345678901"
    assert listing.price == 24.99


def test_parse_item_skips_sold_out() -> None:
    client = object.__new__(MercariRapidApiClient)
    listing = client._parse_item(
        {"id": "m999", "name": "Sold item", "price": 5, "status": "SOLD_OUT"},
        "test",
    )
    assert listing is None


def main() -> int:
    test_extract_list_from_items_key()
    test_parse_item_builds_listing()
    test_parse_item_skips_sold_out()
    print("Mercari parser tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
