"""End-to-end scan pipeline orchestration."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from src.config_loader import AppConfig, BuyRule
from src.filter import filter_listings
from src.listing import Listing
from src.marketplace_factory import create_marketplace_router
from src.notifier_telegram import TelegramNotifier
from src.pricing import effective_max_price
from src.rule_batch import RuleBatchManager
from src.settings import Settings
from src.sheets_logger import SheetsLogger
from src.state import SeenState

logger = logging.getLogger(__name__)


@dataclass
class ScanStats:
    rules_total: int = 0
    rules_scanned: int = 0
    batch_start_index: int = 0
    listings_fetched: int = 0
    listings_qualified: int = 0
    listings_skipped_seen: int = 0
    alerts_sent: int = 0
    alerts_capped: int = 0
    errors: int = 0


class ScanPipeline:
    """Coordinates marketplace search, filtering, dedupe, and outbound notifications."""

    def __init__(self, settings: Settings, config: AppConfig) -> None:
        self._settings = settings
        self._config = config
        self._marketplace = create_marketplace_router(settings)
        self._telegram = TelegramNotifier(settings)
        self._sheets = SheetsLogger(settings)
        self._state = SeenState(
            path=settings.seen_listings_path,
            max_entries=settings.state_max_entries,
        )
        self._rule_batch = RuleBatchManager(
            path=settings.rule_batch_state_path,
            rules_per_run=settings.rules_per_run,
        )

    def _alert_limit_reached(self, stats: ScanStats) -> bool:
        limit = self._settings.max_alerts_per_run
        return limit > 0 and stats.alerts_sent >= limit

    def _process_listing(self, listing: Listing, rule: BuyRule, stats: ScanStats) -> None:
        if self._state.is_seen(listing.dedupe_key):
            stats.listings_skipped_seen += 1
            logger.debug("Skipping already-seen item %s.", listing.dedupe_key)
            return

        if self._alert_limit_reached(stats):
            stats.alerts_capped += 1
            logger.info(
                "Alert cap reached (%d/run); leaving item %s unseen for a later run.",
                self._settings.max_alerts_per_run,
                listing.dedupe_key,
            )
            return

        try:
            self._telegram.send_deal_alert(listing, rule.keyword)
            self._sheets.append_listing(listing, rule.keyword)
        except Exception:
            stats.errors += 1
            logger.exception(
                "Failed to deliver alert for item %s — leaving it unseen for retry.",
                listing.dedupe_key,
            )
            return

        self._state.mark_seen(listing.dedupe_key)
        stats.alerts_sent += 1

    def run_once(self) -> ScanStats:
        """Execute a single scan across the configured buy-rule batch."""
        stats = ScanStats()
        self._state.load()

        selection = self._rule_batch.select_rules(self._config.rules)
        stats.rules_total = selection.total_rules
        stats.batch_start_index = selection.start_index

        if selection.is_full_scan:
            logger.info("Scanning all %d rule(s).", selection.total_rules)
        else:
            logger.info(
                "Scanning rule batch: %d of %d rule(s), starting at index %d.",
                len(selection.rules),
                selection.total_rules,
                selection.start_index,
            )

        for index, rule in enumerate(selection.rules):
            stats.rules_scanned += 1
            rule_number = (selection.start_index + index) % selection.total_rules + 1
            price_cap = effective_max_price(
                rule.max_price,
                self._settings.max_price_tolerance_percent,
            )
            logger.info(
                "Scanning rule %d/%d [%s]: keyword=%r, list_price=%.2f, alert_cap=%.2f",
                rule_number,
                selection.total_rules,
                rule.marketplace,
                rule.keyword,
                rule.max_price,
                price_cap,
            )

            try:
                listings = self._marketplace.search_rule(rule)
            except Exception:
                stats.errors += 1
                logger.exception(
                    "%s search failed for keyword %r.",
                    rule.marketplace,
                    rule.keyword,
                )
                continue

            stats.listings_fetched += len(listings)
            qualified = filter_listings(
                listings,
                rule,
                max_price_tolerance_percent=self._settings.max_price_tolerance_percent,
            )
            stats.listings_qualified += len(qualified)

            for listing in qualified:
                if self._alert_limit_reached(stats):
                    if not self._state.is_seen(listing.dedupe_key):
                        stats.alerts_capped += 1
                    continue
                self._process_listing(listing, rule, stats)

            delay = self._settings.rule_search_delay_seconds
            if delay > 0 and index < len(selection.rules) - 1:
                time.sleep(delay)

        self._rule_batch.advance(stats.rules_scanned, selection.total_rules)
        self._state.prune()
        self._state.save()

        logger.info(
            "Scan complete — rules=%d/%d fetched=%d qualified=%d skipped_seen=%d "
            "alerts=%d capped=%d errors=%d",
            stats.rules_scanned,
            stats.rules_total,
            stats.listings_fetched,
            stats.listings_qualified,
            stats.listings_skipped_seen,
            stats.alerts_sent,
            stats.alerts_capped,
            stats.errors,
        )
        return stats

    def run_connectivity_checks(self) -> None:
        """Verify outbound integrations without running a full marketplace scan."""
        logger.info("Running Telegram connectivity check...")
        self._telegram.send_test_message()
        logger.info("Running Google Sheets connectivity check...")
        self._sheets.verify_connection()
        logger.info("Connectivity checks passed.")
