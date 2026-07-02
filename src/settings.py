"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

VALID_EBAY_BACKENDS = frozenset({"official", "scraperapi"})


class SettingsError(ValueError):
    """Raised when required environment configuration is missing or invalid."""


@dataclass(frozen=True)
class EbaySettings:
    """Settings for marketplace fetch, filter, and dedupe."""

    ebay_backend: str
    scraperapi_key: str | None
    ebay_client_id: str | None
    ebay_client_secret: str | None
    ebay_env: str
    ebay_marketplace_id: str
    config_path: Path
    data_dir: Path
    log_dir: Path
    log_level: str
    state_max_entries: int
    rules_per_run: int
    rule_search_delay_seconds: float
    max_price_tolerance_percent: float
    ebay_us_only: bool
    ebay_buy_it_now_only: bool
    ebay_search_default_limit: int
    ebay_search_max_limit: int

    @property
    def ebay_api_base(self) -> str:
        if self.ebay_env == "sandbox":
            return "https://api.sandbox.ebay.com"
        if self.ebay_env == "production":
            return "https://api.ebay.com"
        raise SettingsError(f"Invalid EBAY_ENV: {self.ebay_env!r}. Use 'production' or 'sandbox'.")

    @property
    def seen_listings_path(self) -> Path:
        return self.data_dir / "seen_listings.json"

    @property
    def rule_batch_state_path(self) -> Path:
        return self.data_dir / "rule_batch_state.json"

    @property
    def uses_scraperapi(self) -> bool:
        return self.ebay_backend == "scraperapi"


@dataclass(frozen=True)
class Settings(EbaySettings):
    """Full application settings including Telegram and Google Sheets."""

    telegram_bot_token: str
    telegram_channel_id: str
    telegram_alert_delay_seconds: float
    telegram_max_retries: int
    google_sheets_id: str
    google_credentials_path: Path
    poll_interval_minutes: int
    max_alerts_per_run: int


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SettingsError(f"Missing required environment variable: {name}")
    return value


def _optional_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise SettingsError(f"{name} must be >= {minimum}, got {value}")
    return value


def _optional_nonneg_int(name: str, default: int) -> int:
    """Integer env var where 0 is valid (often meaning unlimited / all)."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be an integer, got {raw!r}") from exc
    if value < 0:
        raise SettingsError(f"{name} must be >= 0, got {value}")
    return value


def _optional_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise SettingsError(f"{name} must be a boolean (true/false), got {raw!r}")


def _optional_float(name: str, default: float, *, minimum: float = 0.0) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be a number, got {raw!r}") from exc
    if value < minimum:
        raise SettingsError(f"{name} must be >= {minimum}, got {value}")
    return value


def _load_ebay_search_limits() -> tuple[int, int]:
    """Browse API page size defaults (eBay allows up to 200 per request)."""
    default_limit = _optional_int("EBAY_SEARCH_DEFAULT_LIMIT", 100, minimum=1)
    max_limit = _optional_int("EBAY_SEARCH_MAX_LIMIT", 200, minimum=1)
    if max_limit > 200:
        raise SettingsError(
            f"EBAY_SEARCH_MAX_LIMIT must be <= 200 (eBay Browse API cap), got {max_limit}"
        )
    if default_limit > max_limit:
        raise SettingsError(
            f"EBAY_SEARCH_DEFAULT_LIMIT ({default_limit}) must be <= "
            f"EBAY_SEARCH_MAX_LIMIT ({max_limit})"
        )
    return default_limit, max_limit


def _load_common_paths() -> tuple[Path, Path, Path, Path, str, int]:
    config_path = Path(os.getenv("CONFIG_PATH", "./config.yaml"))
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    log_dir = Path(os.getenv("LOG_DIR", "./logs"))
    google_credentials_path = Path(
        os.getenv("GOOGLE_CREDENTIALS_PATH", "./secrets/google-credentials.json")
    )
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    state_max_entries = _optional_int("STATE_MAX_ENTRIES", 10_000, minimum=100)
    return config_path, data_dir, log_dir, google_credentials_path, log_level, state_max_entries


def load_ebay_settings(env_file: str | Path | None = ".env") -> EbaySettings:
    """Load settings for eBay scan, filter, and dedupe only."""
    if env_file is not None:
        load_dotenv(env_file)

    config_path, data_dir, log_dir, _, log_level, state_max_entries = _load_common_paths()
    ebay_env = os.getenv("EBAY_ENV", "production").strip().lower()
    ebay_backend = os.getenv("EBAY_BACKEND", "official").strip().lower()

    if ebay_backend not in VALID_EBAY_BACKENDS:
        raise SettingsError(
            f"Invalid EBAY_BACKEND: {ebay_backend!r}. Use 'official' or 'scraperapi'."
        )

    scraperapi_key: str | None = None
    ebay_client_id: str | None = None
    ebay_client_secret: str | None = None

    if ebay_backend == "scraperapi":
        scraperapi_key = _require("SCRAPERAPI_KEY")
    else:
        ebay_client_id = _require("EBAY_CLIENT_ID")
        ebay_client_secret = _require("EBAY_CLIENT_SECRET")

    ebay_search_default_limit, ebay_search_max_limit = _load_ebay_search_limits()

    return EbaySettings(
        ebay_backend=ebay_backend,
        scraperapi_key=scraperapi_key,
        ebay_client_id=ebay_client_id,
        ebay_client_secret=ebay_client_secret,
        ebay_env=ebay_env,
        ebay_marketplace_id=os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US").strip(),
        config_path=config_path,
        data_dir=data_dir,
        log_dir=log_dir,
        log_level=log_level,
        state_max_entries=state_max_entries,
        rules_per_run=_optional_nonneg_int("RULES_PER_RUN", 8),
        rule_search_delay_seconds=_optional_float("RULE_SEARCH_DELAY_SECONDS", 1.0),
        max_price_tolerance_percent=_optional_float("MAX_PRICE_TOLERANCE_PERCENT", 10.0),
        ebay_us_only=_optional_bool("EBAY_US_ONLY", True),
        ebay_buy_it_now_only=_optional_bool("EBAY_BUY_IT_NOW_ONLY", True),
        ebay_search_default_limit=ebay_search_default_limit,
        ebay_search_max_limit=ebay_search_max_limit,
    )


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    """Load full application settings."""
    if env_file is not None:
        load_dotenv(env_file)

    ebay = load_ebay_settings(env_file=None)
    _, _, _, google_credentials_path, _, _ = _load_common_paths()

    return Settings(
        ebay_backend=ebay.ebay_backend,
        scraperapi_key=ebay.scraperapi_key,
        ebay_client_id=ebay.ebay_client_id,
        ebay_client_secret=ebay.ebay_client_secret,
        ebay_env=ebay.ebay_env,
        ebay_marketplace_id=ebay.ebay_marketplace_id,
        config_path=ebay.config_path,
        data_dir=ebay.data_dir,
        log_dir=ebay.log_dir,
        log_level=ebay.log_level,
        state_max_entries=ebay.state_max_entries,
        rules_per_run=ebay.rules_per_run,
        rule_search_delay_seconds=ebay.rule_search_delay_seconds,
        max_price_tolerance_percent=ebay.max_price_tolerance_percent,
        ebay_us_only=ebay.ebay_us_only,
        ebay_buy_it_now_only=ebay.ebay_buy_it_now_only,
        ebay_search_default_limit=ebay.ebay_search_default_limit,
        ebay_search_max_limit=ebay.ebay_search_max_limit,
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_channel_id=_require("TELEGRAM_CHANNEL_ID"),
        telegram_alert_delay_seconds=_optional_float("TELEGRAM_ALERT_DELAY_SECONDS", 1.5),
        telegram_max_retries=_optional_int("TELEGRAM_MAX_RETRIES", 5),
        google_sheets_id=_require("GOOGLE_SHEETS_ID"),
        google_credentials_path=google_credentials_path,
        poll_interval_minutes=_optional_int("POLL_INTERVAL_MINUTES", 5),
        max_alerts_per_run=_optional_nonneg_int("MAX_ALERTS_PER_RUN", 20),
    )
