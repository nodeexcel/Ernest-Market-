"""Marketplace fetch, filter, and dedupe without notifications."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from src.config_loader import AppConfig, BuyRule
from src.filter import FilterDecision, filter_listings_with_report
from src.listing import Listing
from src.marketplace_factory import create_marketplace_router
from src.pricing import effective_max_price
from src.rule_batch import RuleBatchManager
from src.settings import Settings
from src.state import SeenState

logger = logging.getLogger(__name__)


@dataclass
class RuleScanResult:
    rule: BuyRule
    fetched: int = 0
    qualified: int = 0
    new_deals: list[Listing] = field(default_factory=list)
    skipped_seen: int = 0
    rejected: list[FilterDecision] = field(default_factory=list)
    error: str | None = None


@dataclass
class FilterScanStats:
    rules_scanned: int = 0
    listings_fetched: int = 0
    listings_qualified: int = 0
    new_deals: int = 0
    skipped_seen: int = 0
    errors: int = 0
    rule_results: list[RuleScanResult] = field(default_factory=list)


class FilterScanPipeline:
    """Marketplace → filter → dedupe pipeline (no Telegram or Google Sheets)."""

    def __init__(self, settings: Settings, config: AppConfig) -> None:
        self._settings = settings
        self._config = config
        self._marketplace = create_marketplace_router(settings)
        self._state = SeenState(
            path=settings.seen_listings_path,
            max_entries=settings.state_max_entries,
        )
        self._rule_batch = RuleBatchManager(
            path=settings.rule_batch_state_path,
            rules_per_run=settings.rules_per_run,
        )

    def run_once(self, *, mark_seen: bool = False) -> FilterScanStats:
        stats = FilterScanStats()
        self._state.load()

        selection = self._rule_batch.select_rules(self._config.rules)
        if selection.is_full_scan:
            logger.info("Filter scan: all %d rule(s).", selection.total_rules)
        else:
            logger.info(
                "Filter scan batch: %d of %d rule(s), starting at index %d.",
                len(selection.rules),
                selection.total_rules,
                selection.start_index,
            )

        for index, rule in enumerate(selection.rules):
            result = RuleScanResult(rule=rule)
            stats.rules_scanned += 1
            price_cap = effective_max_price(
                rule.max_price,
                self._settings.max_price_tolerance_percent,
            )
            logger.info(
                "Scanning rule [%s]: keyword=%r, list_price=%.2f, alert_cap=%.2f",
                rule.marketplace,
                rule.keyword,
                rule.max_price,
                price_cap,
            )

            try:
                listings = self._marketplace.search_rule(rule)
            except Exception as exc:
                stats.errors += 1
                result.error = str(exc)
                logger.exception(
                    "%s search failed for keyword %r.",
                    rule.marketplace,
                    rule.keyword,
                )
                stats.rule_results.append(result)
                continue

            result.fetched = len(listings)
            stats.listings_fetched += len(listings)

            qualified, decisions = filter_listings_with_report(
                listings,
                rule,
                max_price_tolerance_percent=self._settings.max_price_tolerance_percent,
                us_listings_only=self._settings.ebay_us_only,
            )
            result.qualified = len(qualified)
            result.rejected = [d for d in decisions if not d.accepted]
            stats.listings_qualified += len(qualified)

            for listing in qualified:
                if self._state.is_seen(listing.dedupe_key):
                    result.skipped_seen += 1
                    stats.skipped_seen += 1
                    continue
                result.new_deals.append(listing)
                stats.new_deals += 1
                if mark_seen:
                    self._state.mark_seen(listing.dedupe_key)

            stats.rule_results.append(result)

            delay = self._settings.rule_search_delay_seconds
            if delay > 0 and index < len(selection.rules) - 1:
                time.sleep(delay)

        self._rule_batch.advance(stats.rules_scanned, selection.total_rules)
        if mark_seen:
            self._state.prune()
            self._state.save()

        logger.info(
            "Filter scan complete — rules=%d fetched=%d qualified=%d new=%d skipped_seen=%d errors=%d",
            stats.rules_scanned,
            stats.listings_fetched,
            stats.listings_qualified,
            stats.new_deals,
            stats.skipped_seen,
            stats.errors,
        )
        return stats
