"""Read deal rows from Google Sheets."""

from __future__ import annotations

import logging
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from src.settings import Settings
from src.sheets_logger import LEGACY_SHEET_HEADERS, SCOPES, SHEET_HEADERS

logger = logging.getLogger(__name__)


class SheetsReaderError(RuntimeError):
    pass


class SheetsReader:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._worksheet: gspread.Worksheet | None = None
        self._header_format: str | None = None

    def _get_worksheet(self) -> gspread.Worksheet:
        if self._worksheet is not None:
            return self._worksheet

        credentials_path = self._settings.google_credentials_path
        if not credentials_path.exists():
            raise SheetsReaderError(
                f"Google credentials file not found: {credentials_path}"
            )

        credentials = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=SCOPES,
        )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(self._settings.google_sheets_id)
        self._worksheet = spreadsheet.sheet1

        first_row = self._worksheet.row_values(1)
        if first_row == list(SHEET_HEADERS):
            self._header_format = "full"
        elif first_row == list(LEGACY_SHEET_HEADERS):
            self._header_format = "legacy"
        else:
            self._header_format = "legacy"

        return self._worksheet

    def _parse_row(self, row: list[Any]) -> dict[str, Any] | None:
        if self._header_format == "full":
            if len(row) < 8:
                return None
            return {
                "timestamp": str(row[0] or ""),
                "marketplace": str(row[1] or "ebay"),
                "keyword": str(row[2] or ""),
                "title": str(row[3] or ""),
                "price": _safe_float(row[4]),
                "currency": str(row[5] or "USD"),
                "url": str(row[6] or ""),
                "item_id": str(row[7] or ""),
                "condition": str(row[8] or "") if len(row) > 8 else "",
            }

        if len(row) < 7:
            return None
        return {
            "timestamp": str(row[0] or ""),
            "marketplace": "ebay",
            "keyword": str(row[1] or ""),
            "title": str(row[2] or ""),
            "price": _safe_float(row[3]),
            "currency": str(row[4] or "USD"),
            "url": str(row[5] or ""),
            "item_id": str(row[6] or ""),
            "condition": str(row[7] or "") if len(row) > 7 else "",
        }

    def fetch_all_deals(self) -> list[dict[str, Any]]:
        worksheet = self._get_worksheet()
        rows = worksheet.get_all_values()
        if len(rows) <= 1:
            return []

        deals: list[dict[str, Any]] = []
        for row in rows[1:]:
            if not any(cell.strip() for cell in row):
                continue
            parsed = self._parse_row(row)
            if parsed and self._is_valid_deal_row(parsed):
                deals.append(parsed)
        deals.reverse()
        return deals

    @staticmethod
    def _is_valid_deal_row(parsed: dict[str, Any]) -> bool:
        item_id = str(parsed.get("item_id", "")).strip()
        keyword = str(parsed.get("keyword", "")).strip().lower()
        title = str(parsed.get("title", "")).strip().lower()
        if not item_id or item_id.upper() == "TEST":
            return False
        if keyword in {"keyword", "marketplace"} and title in {"title", "test"}:
            return False
        if title == "ernest market setup test":
            return False
        return True

    def export_status(self) -> dict[str, Any]:
        try:
            deals = self.fetch_all_deals()
            last_updated = deals[0]["timestamp"] if deals else None
            return {
                "ready": True,
                "row_count": len(deals),
                "last_updated": last_updated,
                "google_sheet_url": (
                    f"https://docs.google.com/spreadsheets/d/{self._settings.google_sheets_id}"
                ),
            }
        except SheetsReaderError:
            return {
                "ready": False,
                "row_count": 0,
                "last_updated": None,
                "google_sheet_url": None,
            }
        except Exception as exc:
            logger.exception("Failed to read Google Sheet: %s", exc)
            return {
                "ready": False,
                "row_count": 0,
                "last_updated": None,
                "google_sheet_url": None,
            }


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
