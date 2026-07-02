"""Google Sheets logging for qualified deals."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

import gspread
from google.oauth2.service_account import Credentials

from src.listing import Listing
from src.settings import Settings

logger = logging.getLogger(__name__)

SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)
SHEET_HEADERS = (
    "Timestamp (UTC)",
    "Marketplace",
    "Keyword",
    "Title",
    "Price",
    "Currency",
    "URL",
    "Item ID",
    "Condition",
)
LEGACY_SHEET_HEADERS = (
    "Timestamp (UTC)",
    "Keyword",
    "Title",
    "Price",
    "Currency",
    "URL",
    "Item ID",
    "Condition",
)
HeaderFormat = Literal["full", "legacy"]


class SheetsLoggerError(RuntimeError):
    """Raised when Google Sheets logging fails."""


class SheetsLogger:
    """Append qualified listings to a Google Sheet."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._worksheet: gspread.Worksheet | None = None
        self._header_format: HeaderFormat | None = None
        self._known_item_ids: set[str] = set()
        self._item_ids_loaded = False

    def _get_worksheet(self) -> gspread.Worksheet:
        if self._worksheet is not None:
            return self._worksheet

        credentials_path = self._settings.google_credentials_path
        if not credentials_path.exists():
            raise SheetsLoggerError(
                f"Google credentials file not found: {credentials_path}. "
                "Download the service account JSON and place it there."
            )

        credentials = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=SCOPES,
        )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(self._settings.google_sheets_id)
        worksheet = spreadsheet.sheet1
        self._header_format = self._ensure_headers(worksheet)
        self._worksheet = worksheet
        return worksheet

    def _default_headers(self) -> tuple[str, ...]:
        return LEGACY_SHEET_HEADERS

    def _ensure_headers(self, worksheet: gspread.Worksheet) -> HeaderFormat:
        first_row = worksheet.row_values(1)
        if first_row == list(SHEET_HEADERS):
            return "full"
        if first_row == list(LEGACY_SHEET_HEADERS):
            return "legacy"
        if not first_row:
            headers = self._default_headers()
            worksheet.append_row(list(headers), value_input_option="USER_ENTERED")
            logger.info("Initialized Google Sheet headers.")
            return "full" if headers == SHEET_HEADERS else "legacy"

        logger.warning(
            "Sheet row 1 headers differ from expected. Expected %s or %s, got %s. "
            "Using legacy row layout for appends.",
            list(SHEET_HEADERS),
            list(LEGACY_SHEET_HEADERS),
            first_row,
        )
        return "legacy"

    def _listing_row(self, listing: Listing, matched_keyword: str, timestamp: str) -> list:
        if self._header_format == "full":
            return [
                timestamp,
                listing.marketplace,
                matched_keyword,
                listing.title,
                listing.price,
                listing.currency,
                listing.url,
                listing.item_id,
                listing.condition,
            ]
        return [
            timestamp,
            matched_keyword,
            listing.title,
            listing.price,
            listing.currency,
            listing.url,
            listing.item_id,
            listing.condition,
        ]

    def _item_id_column_index(self) -> int:
        if self._header_format == "full":
            return 8
        return 7

    def _normalize_item_id(self, value: str) -> str:
        return value.strip()

    def _ensure_item_id_cache(self, worksheet: gspread.Worksheet) -> None:
        if self._item_ids_loaded:
            return

        item_col = self._item_id_column_index()
        column_values = worksheet.col_values(item_col)
        self._known_item_ids = {
            normalized
            for normalized in (self._normalize_item_id(raw) for raw in column_values[1:])
            if normalized
        }
        self._item_ids_loaded = True
        logger.info(
            "Loaded %d existing item ID(s) from Google Sheet for dedupe.",
            len(self._known_item_ids),
        )

    def append_listing(self, listing: Listing, matched_keyword: str) -> None:
        worksheet = self._get_worksheet()
        self._ensure_item_id_cache(worksheet)
        item_id = self._normalize_item_id(listing.item_id)
        if item_id in self._known_item_ids:
            logger.info(
                "Skipping Google Sheet append for existing item ID %s.",
                listing.item_id,
            )
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        row = self._listing_row(listing, matched_keyword, timestamp)
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        self._known_item_ids.add(item_id)
        logger.info("Google Sheet row appended for item %s.", listing.item_id)

    def verify_connection(self) -> None:
        """Confirm the configured spreadsheet is reachable without writing a test row."""
        self._get_worksheet()
        if self._header_format is None:
            raise SheetsLoggerError("Google Sheet headers could not be initialized.")
        logger.info("Google Sheet connection verified.")

    def append_test_row(self) -> None:
        worksheet = self._get_worksheet()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if self._header_format == "full":
            row = [timestamp, "TEST", "TEST", "Ernest Market setup test", 0, "USD", "", "TEST", "N/A"]
        else:
            row = [timestamp, "TEST", "Ernest Market setup test", 0, "USD", "", "TEST", "N/A"]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Google Sheet test row appended.")
