"""Live marketplace scan with filter and dedupe (no Telegram or Sheets)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import ConfigError, load_config
from src.filter_scan import FilterScanPipeline
from src.logging_setup import configure_logging
from src.settings import SettingsError, load_settings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run marketplace fetch, filter, and dedupe without sending alerts.",
    )
    parser.add_argument(
        "--mark-seen",
        action="store_true",
        help="Persist new deals to data/seen_listings.json (default: dry-run only).",
    )
    parser.add_argument(
        "--verbose-rejects",
        action="store_true",
        help="Print rejection reasons for filtered-out listings.",
    )
    return parser.parse_args()


def _safe_print(text: str) -> None:
    """Print safely on Windows consoles that lack full Unicode support."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(text.encode(encoding, errors="replace").decode(encoding))


def main() -> int:
    args = _parse_args()

    try:
        settings = load_settings()
        config = load_config(settings.config_path, mirror_mercari=settings.mercari_enabled)
    except (SettingsError, ConfigError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    configure_logging(settings)
    pipeline = FilterScanPipeline(settings, config)
    stats = pipeline.run_once(mark_seen=args.mark_seen)

    mode = "LIVE (mark-seen)" if args.mark_seen else "DRY-RUN"
    _safe_print(f"\n=== Scan ({mode}) ===")
    _safe_print(
        f"Rules: {stats.rules_scanned} | Fetched: {stats.listings_fetched} | "
        f"Qualified: {stats.listings_qualified} | New: {stats.new_deals} | "
        f"Skipped (seen): {stats.skipped_seen} | Errors: {stats.errors}"
    )
    _safe_print("")

    for result in stats.rule_results:
        _safe_print(f"Rule: {result.rule.keyword!r} (max ${result.rule.max_price:.2f})")
        if result.error:
            _safe_print(f"  ERROR: {result.error}")
            continue
        _safe_print(
            f"  Fetched: {result.fetched} | Qualified: {result.qualified} | "
            f"New: {len(result.new_deals)}"
        )

        if args.verbose_rejects and result.rejected:
            reason_counts: dict[str, int] = {}
            for decision in result.rejected:
                key = decision.reason.value if decision.reason else "unknown"
                reason_counts[key] = reason_counts.get(key, 0) + 1
            _safe_print(f"  Rejected: {dict(reason_counts)}")

        for listing in result.new_deals[:15]:
            _safe_print(f"  NEW  ${listing.price:.2f} — {listing.title}")
            _safe_print(f"       {listing.url}")
        if len(result.new_deals) > 15:
            _safe_print(f"  ... and {len(result.new_deals) - 15} more")
        _safe_print("")

    if stats.new_deals == 0 and stats.errors == 0:
        _safe_print("No new deals this run.")
    elif not args.mark_seen and stats.new_deals > 0:
        _safe_print("Dry-run only — re-run with --mark-seen to persist seen IDs.")

    return 1 if stats.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
