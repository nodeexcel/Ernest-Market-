"""Normalized marketplace listing model."""

from __future__ import annotations

from dataclasses import dataclass

VALID_MARKETPLACES = frozenset({"ebay", "mercari"})


@dataclass(frozen=True)
class Listing:
    item_id: str
    title: str
    price: float
    currency: str
    url: str
    condition: str
    keyword: str
    marketplace: str = "ebay"

    def __post_init__(self) -> None:
        if self.marketplace not in VALID_MARKETPLACES:
            raise ValueError(
                f"Invalid marketplace {self.marketplace!r}. Use 'ebay' or 'mercari'."
            )

    @property
    def dedupe_key(self) -> str:
        return f"{self.marketplace}:{self.item_id}"
