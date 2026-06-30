"""Shared FastAPI dependencies."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.history_store import HistoryStore
from api.services.scan_runner import ScanRunner
from src.settings import Settings, SettingsError, load_settings
from src.state import SeenState

_settings: Settings | None = None
_scan_runner: ScanRunner | None = None
_history_store: HistoryStore | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
        _settings.data_dir.mkdir(parents=True, exist_ok=True)
    return _settings


def get_history_store() -> HistoryStore:
    global _history_store
    if _history_store is None:
        settings = get_settings()
        _history_store = HistoryStore(settings.data_dir / "scan_history.json")
    return _history_store


def get_scan_runner() -> ScanRunner:
    global _scan_runner
    if _scan_runner is None:
        settings = get_settings()
        _scan_runner = ScanRunner(
            settings,
            get_history_store(),
            settings.log_dir / "app.log",
        )
    return _scan_runner


def get_seen_state() -> SeenState:
    settings = get_settings()
    state = SeenState(
        path=settings.seen_listings_path,
        max_entries=settings.state_max_entries,
    )
    state.load()
    return state
