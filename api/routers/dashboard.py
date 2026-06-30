"""Dashboard overview endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.dependencies import get_history_store, get_scan_runner, get_seen_state, get_settings
from api.schemas import DashboardOverview, ScanStatsResponse
from api.services.sheets_reader import SheetsReader
from src.config_loader import ConfigError, load_config

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def get_overview() -> DashboardOverview:
    try:
        settings = get_settings()
        config = load_config(settings.config_path)
    except (ConfigError, Exception) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    seen = get_seen_state()
    scan_status = get_scan_runner().get_status()
    history = get_history_store().last_entry()

    last_scan_at = None
    last_scan_status = None
    last_stats = None

    if scan_status.get("completed_at"):
        last_scan_at = scan_status["completed_at"]
        last_scan_status = scan_status["status"]
        if scan_status.get("stats"):
            last_stats = ScanStatsResponse(**scan_status["stats"])
    elif history and history.completed_at:
        last_scan_at = history.completed_at
        last_scan_status = history.status
        if history.stats:
            last_stats = ScanStatsResponse(**history.stats)

    total_deals = 0
    try:
        reader = SheetsReader(settings)
        total_deals = reader.export_status()["row_count"]
    except Exception:
        total_deals = 0

    return DashboardOverview(
        total_rules=len(config.rules),
        seen_listings=seen.count(),
        seen_capacity=settings.state_max_entries,
        last_scan_at=last_scan_at,
        last_scan_status=last_scan_status,
        total_deals_logged=total_deals,
        ebay_backend=settings.ebay_backend,
        poll_interval_minutes=settings.poll_interval_minutes,
        rules_per_run=settings.rules_per_run,
        max_alerts_per_run=settings.max_alerts_per_run,
        processing_status=scan_status["status"],
        last_stats=last_stats,
    )
