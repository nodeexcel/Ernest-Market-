"""CLI helper to verify Telegram bot and channel setup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.logging_setup import configure_logging
from src.notifier_telegram import TelegramNotifier, TelegramNotifierError
from src.settings import SettingsError, load_settings


def main() -> int:
    try:
        settings = load_settings()
    except SettingsError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    configure_logging(settings)
    notifier = TelegramNotifier(settings)

    try:
        notifier.send_test_message("Ernest Market — Telegram setup test successful.")
    except TelegramNotifierError as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1

    print("Telegram test message sent. Check your private channel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
