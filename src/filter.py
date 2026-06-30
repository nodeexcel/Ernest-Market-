"""Listing filter logic against buy rules."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

from src.config_loader import BuyRule
from src.listing import Listing

logger = logging.getLogger(__name__)


class RejectReason(str, Enum):
    KEYWORD_MISMATCH = "keyword_not_in_title"
    PRICE_TOO_LOW = "price_below_min"
    PRICE_TOO_HIGH = "price_above_max"
    EXCLUDED_WORD = "excluded_word"
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


def evaluate_listing(listing: Listing, rule: BuyRule) -> FilterDecision:
    """Evaluate a single listing and return an accept/reject decision with reason."""
    if listing.keyword != rule.keyword:
        return FilterDecision(listing, False, RejectReason.WRONG_RULE)

    if listing.price < rule.min_price:
        return FilterDecision(listing, False, RejectReason.PRICE_TOO_LOW)

    if listing.price > rule.max_price:
        return FilterDecision(listing, False, RejectReason.PRICE_TOO_HIGH)

    search_text = listing.title
    if rule.match_in == "title_and_description":
        search_text = listing.title

    if not _keyword_matches(search_text, rule.keyword):
        return FilterDecision(listing, False, RejectReason.KEYWORD_MISMATCH)

    excluded = _contains_excluded_word(search_text, rule.exclude_words)
    if excluded is not None:
        return FilterDecision(listing, False, RejectReason.EXCLUDED_WORD)

    return FilterDecision(listing, True)


def matches_rule(listing: Listing, rule: BuyRule) -> bool:
    """Return True when a listing satisfies keyword, price window, and exclude filters."""
    return evaluate_listing(listing, rule).accepted


def filter_listings(listings: list[Listing], rule: BuyRule) -> list[Listing]:
    """Filter a batch of listings for a single rule."""
    matched = [listing for listing in listings if matches_rule(listing, rule)]
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
) -> tuple[list[Listing], list[FilterDecision]]:
    """Filter listings and return both matches and full decision report."""
    decisions = [evaluate_listing(listing, rule) for listing in listings]
    matched = [decision.listing for decision in decisions if decision.accepted]
    logger.info(
        "Filter for %r: %d/%d listing(s) qualified.",
        rule.keyword,
        len(matched),
        len(listings),
    )
    return matched, decisions
