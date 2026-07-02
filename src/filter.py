"""Listing filter logic against buy rules."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

from src.config_loader import BuyRule
from src.listing import Listing
from src.ebay_search_filters import title_suggests_international
from src.pricing import effective_max_price

logger = logging.getLogger(__name__)

# eBay condition labels and title phrases that are not factory-sealed retail boxes.
_REJECTED_CONDITION_PHRASES = frozenset(
    {
        "open box",
        "pre-owned",
        "pre owned",
        "preowned",
        "used",
        "for parts",
        "refurbished",
        "seller refurbished",
        "certified refurbished",
        "heavily used",
        "acceptable",
        "damaged",
        "not working",
        "not functional",
    }
)


class RejectReason(str, Enum):
    KEYWORD_MISMATCH = "keyword_not_in_title"
    PRICE_TOO_LOW = "price_below_min"
    PRICE_TOO_HIGH = "price_above_max"
    EXCLUDED_WORD = "excluded_word"
    BAD_CONDITION = "condition_not_acceptable"
    INTERNATIONAL_LISTING = "international_listing"
    WRONG_RULE = "wrong_search_rule"


@dataclass(frozen=True)
class FilterDecision:
    listing: Listing
    accepted: bool
    reason: RejectReason | None = None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _keyword_matches(text: str, keyword: str) -> bool:
    """Match keyword as substring; multi-word keywords require all words present."""
    normalized_text = _normalize(text)
    normalized_keyword = _normalize(keyword)
    if not normalized_keyword:
        return False
    if " " not in normalized_keyword:
        return normalized_keyword in normalized_text
    return all(part in normalized_text for part in normalized_keyword.split())


def _contains_excluded_word(text: str, exclude_words: list[str]) -> str | None:
    lowered = _normalize(text)
    for word in exclude_words:
        if word and word.lower() in lowered:
            return word
    return None


def _condition_is_rejected(condition: str, title: str) -> bool:
    for field in (condition, title):
        normalized = _normalize(field)
        if not normalized:
            continue
        for phrase in _REJECTED_CONDITION_PHRASES:
            if phrase in normalized:
                return True
    return False


def evaluate_listing(
    listing: Listing,
    rule: BuyRule,
    *,
    max_price_tolerance_percent: float = 0.0,
    us_listings_only: bool = True,
) -> FilterDecision:
    """Evaluate a single listing and return an accept/reject decision with reason."""
    if listing.keyword != rule.keyword:
        return FilterDecision(listing, False, RejectReason.WRONG_RULE)

    price_cap = effective_max_price(rule.max_price, max_price_tolerance_percent)

    if listing.price < rule.min_price:
        return FilterDecision(listing, False, RejectReason.PRICE_TOO_LOW)

    if listing.price > price_cap:
        return FilterDecision(listing, False, RejectReason.PRICE_TOO_HIGH)

    search_text = listing.title
    if rule.match_in == "title_and_description":
        search_text = listing.title

    if not _keyword_matches(search_text, rule.keyword):
        return FilterDecision(listing, False, RejectReason.KEYWORD_MISMATCH)

    if _condition_is_rejected(listing.condition, listing.title):
        return FilterDecision(listing, False, RejectReason.BAD_CONDITION)

    if us_listings_only and title_suggests_international(search_text):
        return FilterDecision(listing, False, RejectReason.INTERNATIONAL_LISTING)

    excluded = _contains_excluded_word(search_text, rule.exclude_words)
    if excluded is not None:
        return FilterDecision(listing, False, RejectReason.EXCLUDED_WORD)

    return FilterDecision(listing, True)


def matches_rule(
    listing: Listing,
    rule: BuyRule,
    *,
    max_price_tolerance_percent: float = 0.0,
    us_listings_only: bool = True,
) -> bool:
    """Return True when a listing satisfies keyword, price window, and exclude filters."""
    return evaluate_listing(
        listing,
        rule,
        max_price_tolerance_percent=max_price_tolerance_percent,
        us_listings_only=us_listings_only,
    ).accepted


def filter_listings(
    listings: list[Listing],
    rule: BuyRule,
    *,
    max_price_tolerance_percent: float = 0.0,
    us_listings_only: bool = True,
) -> list[Listing]:
    """Filter a batch of listings for a single rule."""
    matched = [
        listing
        for listing in listings
        if matches_rule(
            listing,
            rule,
            max_price_tolerance_percent=max_price_tolerance_percent,
            us_listings_only=us_listings_only,
        )
    ]
    logger.info(
        "Filter for %r: %d/%d listing(s) qualified.",
        rule.keyword,
        len(matched),
        len(listings),
    )
    return matched


def filter_listings_with_report(
    listings: list[Listing],
    rule: BuyRule,
    *,
    max_price_tolerance_percent: float = 0.0,
    us_listings_only: bool = True,
) -> tuple[list[Listing], list[FilterDecision]]:
    """Filter listings and return both matches and full decision report."""
    decisions = [
        evaluate_listing(
            listing,
            rule,
            max_price_tolerance_percent=max_price_tolerance_percent,
            us_listings_only=us_listings_only,
        )
        for listing in listings
    ]
    matched = [decision.listing for decision in decisions if decision.accepted]
    logger.info(
        "Filter for %r: %d/%d listing(s) qualified.",
        rule.keyword,
        len(matched),
        len(listings),
    )
    return matched, decisions
