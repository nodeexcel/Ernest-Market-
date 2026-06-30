"""eBay OAuth token management with in-memory caching."""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass

import requests

from src.settings import EbaySettings

logger = logging.getLogger(__name__)

OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"
TOKEN_REFRESH_BUFFER_SECONDS = 120


class EbayAuthError(RuntimeError):
    """Raised when eBay OAuth token retrieval fails."""


@dataclass
class _TokenCache:
    access_token: str | None = None
    expires_at: float = 0.0

    def is_valid(self) -> bool:
        return bool(self.access_token) and time.time() < (
            self.expires_at - TOKEN_REFRESH_BUFFER_SECONDS
        )


class EbayAuthClient:
    """Fetches and caches eBay application access tokens."""

    def __init__(self, settings: EbaySettings, session: requests.Session | None = None) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        self._cache = _TokenCache()

    @property
    def _token_url(self) -> str:
        return f"{self._settings.ebay_api_base}/identity/v1/oauth2/token"

    def _basic_auth_header(self) -> str:
        credentials = f"{self._settings.ebay_client_id}:{self._settings.ebay_client_secret}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded}"

    def get_access_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and self._cache.is_valid():
            assert self._cache.access_token is not None
            return self._cache.access_token

        logger.info("Requesting new eBay OAuth access token (env=%s).", self._settings.ebay_env)
        response = self._session.post(
            self._token_url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": self._basic_auth_header(),
            },
            data={
                "grant_type": "client_credentials",
                "scope": OAUTH_SCOPE,
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise EbayAuthError(
                f"eBay OAuth failed ({response.status_code}): {response.text[:500]}"
            )

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")

        if not access_token or not isinstance(expires_in, (int, float)):
            raise EbayAuthError(f"Unexpected eBay OAuth response: {payload}")

        self._cache.access_token = access_token
        self._cache.expires_at = time.time() + float(expires_in)
        logger.debug("eBay token acquired; expires in %s seconds.", expires_in)
        return access_token

    def invalidate(self) -> None:
        self._cache = _TokenCache()
