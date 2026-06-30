"""Telegram channel notifications."""

from __future__ import annotations

import logging
import re
import time

import requests

from src.listing import Listing
from src.settings import Settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT_SECONDS = 30
_RETRY_AFTER_RE = re.compile(r"retry after (\d+)", re.IGNORECASE)


class TelegramNotifierError(RuntimeError):
    """Raised when Telegram notification delivery fails."""


class TelegramNotifier:
    """Send deal alerts to a private Telegram channel."""

    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        self._settings = settings
        self._session = session or requests.Session()

    @property
    def _send_message_url(self) -> str:
        return f"{TELEGRAM_API_BASE}/bot{self._settings.telegram_bot_token}/sendMessage"

    @staticmethod
    def format_message(listing: Listing, matched_keyword: str) -> str:
        label = listing.marketplace.capitalize()
        return (
            f"🔔 {label} Match: {matched_keyword}\n"
            f"${listing.price:.2f} {listing.currency} — {listing.title}\n"
            f"Condition: {listing.condition}\n"
            f"{listing.url}"
        )

    @staticmethod
    def parse_retry_after(response: requests.Response) -> int | None:
        """Extract Telegram retry_after seconds from a 429 response."""
        try:
            payload = response.json()
        except ValueError:
            return None

        if payload.get("error_code") != 429:
            return None

        parameters = payload.get("parameters") or {}
        retry_after = parameters.get("retry_after")
        if retry_after is not None:
            try:
                return max(1, int(retry_after))
            except (TypeError, ValueError):
                pass

        description = str(payload.get("description", ""))
        match = _RETRY_AFTER_RE.search(description)
        if match:
            return max(1, int(match.group(1)))
        return None

    def _pace_after_send(self) -> None:
        delay = self._settings.telegram_alert_delay_seconds
        if delay > 0:
            time.sleep(delay)

    def _post_message(self, payload: dict) -> requests.Response:
        return self._session.post(
            self._send_message_url,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    def _send_with_retries(self, payload: dict, *, context: str) -> None:
        max_retries = self._settings.telegram_max_retries
        last_error = "unknown error"

        for attempt in range(1, max_retries + 1):
            response = self._post_message(payload)

            if response.status_code == 200:
                body = response.json()
                if body.get("ok"):
                    self._pace_after_send()
                    return
                last_error = f"Telegram API returned error: {body}"
            elif response.status_code == 429:
                retry_after = self.parse_retry_after(response) or 2
                last_error = response.text[:500]
                logger.warning(
                    "Telegram rate limited (%s); waiting %d second(s) before retry %d/%d.",
                    context,
                    retry_after,
                    attempt,
                    max_retries,
                )
                time.sleep(retry_after)
                continue
            else:
                last_error = response.text[:500]
                if attempt < max_retries:
                    backoff = min(2 ** attempt, 30)
                    logger.warning(
                        "Telegram request failed (%s, HTTP %d); retrying in %d second(s).",
                        context,
                        response.status_code,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue

            break

        raise TelegramNotifierError(
            f"Telegram {context} failed after {max_retries} attempt(s): {last_error}"
        )

    def send_deal_alert(self, listing: Listing, matched_keyword: str) -> None:
        message = self.format_message(listing, matched_keyword)
        self._send_with_retries(
            {
                "chat_id": self._settings.telegram_channel_id,
                "text": message,
                "disable_web_page_preview": False,
            },
            context=f"sendMessage item {listing.item_id}",
        )
        logger.info("Telegram alert sent for item %s.", listing.item_id)

    def send_test_message(self, text: str = "Ernest Market monitor test message.") -> None:
        self._send_with_retries(
            {
                "chat_id": self._settings.telegram_channel_id,
                "text": text,
            },
            context="test message",
        )
        logger.info("Telegram test message delivered.")
