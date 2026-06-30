"""Pydantic models for the dashboard API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ScanProgress(BaseModel):
    current: int = 0
    total: int = 0
    percent: float = 0.0


class ScanStatsResponse(BaseModel):
    rules_total: int = 0
    rules_scanned: int = 0
    batch_start_index: int = 0
    listings_fetched: int = 0
    listings_qualified: int = 0
    listings_skipped_seen: int = 0
    alerts_sent: int = 0
    alerts_capped: int = 0
    errors: int = 0


class ScanStatusResponse(BaseModel):
    status: Literal["idle", "running", "completed", "failed"] = "idle"
    mode: Literal["full", "dry_run"] | None = None
    current_step: str | None = None
    progress: ScanProgress = Field(default_factory=ScanProgress)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    stats: ScanStatsResponse | None = None


class DashboardOverview(BaseModel):
    total_rules: int
    seen_listings: int
    seen_capacity: int
    last_scan_at: str | None
    last_scan_status: str | None
    total_deals_logged: int
    ebay_backend: str
    poll_interval_minutes: int
    rules_per_run: int
    max_alerts_per_run: int
    processing_status: Literal["idle", "running", "completed", "failed"]
    last_stats: ScanStatsResponse | None = None


class LogLine(BaseModel):
    timestamp: str | None
    level: str | None
    message: str


class DealRow(BaseModel):
    timestamp: str
    marketplace: str
    keyword: str
    title: str
    price: float
    currency: str
    url: str
    item_id: str
    condition: str


class DealsPage(BaseModel):
    items: list[DealRow]
    total: int
    page: int
    page_size: int
    total_pages: int


class BuyRuleSchema(BaseModel):
    keyword: str
    max_price: float
    min_price: float = 0.0
    match_in: str = "title"
    exclude_words: list[str] = Field(default_factory=list)
    marketplace: str = "ebay"


class RulesConfigResponse(BaseModel):
    rules: list[BuyRuleSchema]
    rule_count: int


class AppSettingsResponse(BaseModel):
    poll_interval_minutes: int
    rules_per_run: int
    max_alerts_per_run: int
    rule_search_delay_seconds: float
    ebay_backend: str
    ebay_marketplace_id: str
    google_sheets_configured: bool
    telegram_configured: bool


class HistoryEntry(BaseModel):
    id: str
    started_at: str
    completed_at: str | None
    status: Literal["completed", "failed"]
    mode: Literal["full", "dry_run"]
    stats: ScanStatsResponse | None = None
    error: str | None = None


class StartScanRequest(BaseModel):
    mode: Literal["full", "dry_run"] = "full"


class MessageResponse(BaseModel):
    message: str
    detail: dict[str, Any] | None = None


class ExportStatusResponse(BaseModel):
    ready: bool
    row_count: int
    last_updated: str | None
    google_sheet_url: str | None
