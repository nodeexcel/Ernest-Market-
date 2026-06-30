"""Ernest Market — eBay deal monitor entry point."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import ConfigError, load_config
from src.logging_setup import configure_logging
from src.pipeline import ScanPipeline
from src.settings import SettingsError, load_settings

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor eBay listings and alert qualified deals to Telegram and Google Sheets.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scan and exit (recommended for Task Scheduler).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify Telegram and Google Sheets connectivity only.",
    )
    return parser.parse_args()


def _run_loop(pipeline: ScanPipeline, interval_minutes: int) -> None:
    interval_seconds = interval_minutes * 60
    logger.info("Starting loop mode — interval=%d minute(s). Press Ctrl+C to stop.", interval_minutes)

    while True:
        try:
            pipeline.run_once()
        except Exception:
            logger.exception("Unexpected error during scan cycle.")

        logger.info("Sleeping %d second(s) until next scan.", interval_seconds)
        time.sleep(interval_seconds)


def main() -> int:
    args = _parse_args()

    try:
        settings = load_settings()
        config = load_config(settings.config_path)
    except (SettingsError, ConfigError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    configure_logging(settings)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    pipeline = ScanPipeline(settings, config)

    if args.check:
        try:
            pipeline.run_connectivity_checks()
        except Exception:
            logger.exception("Connectivity check failed.")
            return 1
        return 0

    if args.once:
        try:
            pipeline.run_once()
        except Exception:
            logger.exception("Scan failed.")
            return 1
        return 0

    try:
        _run_loop(pipeline, settings.poll_interval_minutes)
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
