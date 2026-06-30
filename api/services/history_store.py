"""Persist scan run history for the dashboard."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


@dataclass
class HistoryRecord:
    id: str
    started_at: str
    completed_at: str | None
    status: Literal["completed", "failed"]
    mode: Literal["full", "dry_run"]
    stats: dict[str, Any] | None = None
    error: str | None = None


class HistoryStore:
    def __init__(self, path: Path, *, max_entries: int = 50) -> None:
        self._path = path
        self._max_entries = max_entries

    def _load(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            with self._path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return []
        entries = payload.get("entries", [])
        return entries if isinstance(entries, list) else []

    def _save(self, entries: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entries": entries[: self._max_entries],
        }
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    @staticmethod
    def _to_record(entry: dict[str, Any]) -> HistoryRecord:
        """Drop internal persistence keys (e.g. ``_running``) before building a record."""
        clean = {key: value for key, value in entry.items() if not key.startswith("_")}
        return HistoryRecord(**clean)

    def list_entries(self) -> list[HistoryRecord]:
        return [self._to_record(entry) for entry in self._load()]

    def get(self, entry_id: str) -> HistoryRecord | None:
        for entry in self._load():
            if entry.get("id") == entry_id:
                return self._to_record(entry)
        return None

    def add_running(self, mode: Literal["full", "dry_run"]) -> str:
        entry_id = str(uuid.uuid4())
        entries = self._load()
        entries.insert(
            0,
            {
                "id": entry_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
                "status": "completed",
                "mode": mode,
                "stats": None,
                "error": None,
                "_running": True,
            },
        )
        self._save(entries)
        return entry_id

    def complete(
        self,
        entry_id: str,
        *,
        status: Literal["completed", "failed"],
        stats: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        entries = self._load()
        for entry in entries:
            if entry.get("id") != entry_id:
                continue
            entry["completed_at"] = datetime.now(timezone.utc).isoformat()
            entry["status"] = status
            entry["stats"] = stats
            entry["error"] = error
            entry.pop("_running", None)
            break
        self._save(entries)

    def last_entry(self) -> HistoryRecord | None:
        entries = self.list_entries()
        return entries[0] if entries else None
