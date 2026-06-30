"""Shared ScraperAPI HTTP fetch for marketplace HTML pages."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

SCRAPERAPI_ENDPOINT = "https://api.scraperapi.com"
DEFAULT_TIMEOUT_SECONDS = 90


class ScraperApiError(RuntimeError):
    """Raised when ScraperAPI returns a non-success response."""


def fetch_html(
    api_key: str,
    target_url: str,
    *,
    session: requests.Session | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    country_code: str = "us",
    render: bool = False,
    premium: bool = False,
    ultra_premium: bool = False,
) -> str:
    """Fetch a target URL through ScraperAPI and return HTML text."""
    if not api_key.strip():
        raise ScraperApiError("SCRAPERAPI_KEY is required.")

    params: dict[str, str] = {
        "api_key": api_key.strip(),
        "url": target_url,
        "country_code": country_code,
    }
    if render:
        params["render"] = "true"
    if premium:
        params["premium"] = "true"
    if ultra_premium:
        params["ultra_premium"] = "true"

    http = session or requests.Session()
    logger.info(
        "ScraperAPI fetching %s (render=%s, premium=%s, ultra_premium=%s)",
        target_url,
        render,
        premium,
        ultra_premium,
    )
    response = http.get(SCRAPERAPI_ENDPOINT, params=params, timeout=timeout)
    if response.status_code != 200:
        raise ScraperApiError(
            f"ScraperAPI request failed ({response.status_code}): {response.text[:500]}"
        )
    return response.text
