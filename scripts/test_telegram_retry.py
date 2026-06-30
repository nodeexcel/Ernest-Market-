"""Offline tests for Telegram 429 retry parsing."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.notifier_telegram import TelegramNotifier


def test_parse_retry_after_from_parameters() -> None:
    response = Mock()
    response.json.return_value = {
        "ok": False,
        "error_code": 429,
        "description": "Too Many Requests: retry after 19",
        "parameters": {"retry_after": 19},
    }
    assert TelegramNotifier.parse_retry_after(response) == 19


def test_parse_retry_after_from_description() -> None:
    response = Mock()
    response.json.return_value = {
        "ok": False,
        "error_code": 429,
        "description": "Too Many Requests: retry after 12",
    }
    assert TelegramNotifier.parse_retry_after(response) == 12


def test_parse_retry_after_non_429() -> None:
    response = Mock()
    response.json.return_value = {"ok": False, "error_code": 400, "description": "Bad Request"}
    assert TelegramNotifier.parse_retry_after(response) is None


def main() -> int:
    test_parse_retry_after_from_parameters()
    test_parse_retry_after_from_description()
    test_parse_retry_after_non_429()
    print("Telegram retry parsing tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
