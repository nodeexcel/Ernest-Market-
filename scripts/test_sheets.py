"""CLI helper to verify Google Sheets service account setup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.logging_setup import configure_logging
from src.settings import SettingsError, load_settings
from src.sheets_logger import SheetsLogger, SheetsLoggerError


def main() -> int:
    try:
        settings = load_settings()
    except SettingsError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    configure_logging(settings)
    logger = SheetsLogger(settings)

    try:
        logger.append_test_row()
    except SheetsLoggerError as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1

    print("Google Sheets test row appended. Open your spreadsheet to verify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
