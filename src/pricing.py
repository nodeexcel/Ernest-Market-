"""Price limit helpers for buy rules."""

from __future__ import annotations


def effective_max_price(list_price: float, tolerance_percent: float) -> float:
    """Apply an optional percentage buffer above the configured list/payout price."""
    if tolerance_percent <= 0:
        return list_price
    return round(list_price * (1 + tolerance_percent / 100), 2)
