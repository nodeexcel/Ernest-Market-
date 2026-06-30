"""Background scan execution with live status tracking."""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from api.services.history_store import HistoryStore
from api.services.log_reader import parse_scan_complete, parse_scanning_progress, tail_log
from src.config_loader import load_config
from src.filter_scan import FilterScanPipeline
from src.logging_setup import configure_logging
from src.pipeline import ScanPipeline
from src.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class ScanState:
    status: Literal["idle", "running", "completed", "failed"] = "idle"
    mode: Literal["full", "dry_run"] | None = None
    current_step: str | None = None
    progress_current: int = 0
    progress_total: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    stats: dict[str, Any] | None = None
    history_id: str | None = None
    _log_offset: int = field(default=0, repr=False)


class ScanRunner:
    def __init__(self, settings: Settings, history_store: HistoryStore, log_path: Path) -> None:
        self._settings = settings
        self._history = history_store
        self._log_path = log_path
        self._lock = threading.Lock()
        self._state = ScanState()
        self._thread: threading.Thread | None = None

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            state = self._state
            percent = 0.0
            if state.progress_total > 0:
                percent = round((state.progress_current / state.progress_total) * 100, 1)

            return {
                "status": state.status,
                "mode": state.mode,
                "current_step": state.current_step,
                "progress": {
                    "current": state.progress_current,
                    "total": state.progress_total,
                    "percent": percent,
                },
                "started_at": state.started_at,
                "completed_at": state.completed_at,
                "error": state.error,
                "stats": state.stats,
            }

    def start(self, mode: Literal["full", "dry_run"] = "full") -> bool:
        with self._lock:
            if self._state.status == "running":
                return False

            self._state = ScanState(
                status="running",
                mode=mode,
                current_step="Initializing scan pipeline…",
                started_at=datetime.now(timezone.utc).isoformat(),
                _log_offset=self._log_line_count(),
            )
            history_id = self._history.add_running(mode)
            self._state.history_id = history_id

        thread = threading.Thread(target=self._run_scan, args=(mode, history_id), daemon=True)
        self._thread = thread
        thread.start()
        return True

    def _log_line_count(self) -> int:
        if not self._log_path.exists():
            return 0
        try:
            with self._log_path.open(encoding="utf-8", errors="replace") as handle:
                return sum(1 for _ in handle)
        except OSError:
            return 0

    def _poll_logs(self) -> None:
        if not self._log_path.exists():
            return

        try:
            with self._log_path.open(encoding="utf-8", errors="replace") as handle:
                lines = handle.readlines()
        except OSError:
            return

        with self._lock:
            offset = self._state._log_offset

        for line in lines[offset:]:
            message = line.strip()
            if not message:
                continue
            parts = message.split(" - ", 3)
            if len(parts) >= 4:
                message = parts[3]

            progress = parse_scanning_progress(message)
            if progress:
                current, total, step = progress
                with self._lock:
                    self._state.progress_current = current
                    self._state.progress_total = total
                    self._state.current_step = step

            complete = parse_scan_complete(message)
            if complete:
                with self._lock:
                    self._state.stats = complete

        with self._lock:
            self._state._log_offset = len(lines)

    def _run_scan(self, mode: Literal["full", "dry_run"], history_id: str) -> None:
        try:
            configure_logging(self._settings)
            config = load_config(self._settings.config_path)

            with self._lock:
                self._state.current_step = "Loading buy rules and marketplace clients…"

            if mode == "dry_run":
                pipeline = FilterScanPipeline(self._settings, config)
                with self._lock:
                    self._state.current_step = "Running dry-run scan (no alerts)…"
                stats = pipeline.run_once(mark_seen=False)
                stats_dict = {
                    "rules_total": len(config.rules),
                    "rules_scanned": stats.rules_scanned,
                    "batch_start_index": 0,
                    "listings_fetched": stats.listings_fetched,
                    "listings_qualified": stats.listings_qualified,
                    "listings_skipped_seen": stats.skipped_seen,
                    "alerts_sent": stats.new_deals,
                    "alerts_capped": 0,
                    "errors": stats.errors,
                }
            else:
                pipeline = ScanPipeline(self._settings, config)
                with self._lock:
                    self._state.current_step = "Running full scan with alerts…"
                result = pipeline.run_once()
                stats_dict = asdict(result)

            self._poll_logs()

            with self._lock:
                self._state.status = "completed"
                self._state.completed_at = datetime.now(timezone.utc).isoformat()
                self._state.stats = stats_dict
                self._state.current_step = "Scan completed successfully"
                if self._state.progress_total == 0:
                    self._state.progress_total = stats_dict.get("rules_total", 0)
                    self._state.progress_current = stats_dict.get("rules_scanned", 0)

            self._history.complete(history_id, status="completed", stats=stats_dict)

        except Exception as exc:
            logger.exception("Dashboard scan failed.")
            with self._lock:
                self._state.status = "failed"
                self._state.completed_at = datetime.now(timezone.utc).isoformat()
                self._state.error = str(exc)
                self._state.current_step = "Scan failed"
            self._history.complete(history_id, status="failed", error=str(exc))

    def get_recent_logs(self, *, max_lines: int = 80) -> list[dict[str, str | None]]:
        if self._state.status == "running":
            self._poll_logs()
        return tail_log(self._log_path, max_lines=max_lines)
