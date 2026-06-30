"""Persistent deduplication state for seen listing IDs."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_VERSION = 1


@dataclass
class SeenState:
    """Tracks listing IDs that have already been alerted."""

    path: Path
    max_entries: int = 10_000
    seen: dict[str, str] = field(default_factory=dict)

    def is_seen(self, dedupe_key: str) -> bool:
        if dedupe_key in self.seen:
            return True
        if dedupe_key.startswith("ebay:"):
            legacy_key = dedupe_key[5:]
            return legacy_key in self.seen
        return False

    def mark_seen(self, item_id: str) -> None:
        self.seen[item_id] = datetime.now(timezone.utc).isoformat()

    def unseen_from(self, item_ids: list[str]) -> list[str]:
        return [item_id for item_id in item_ids if not self.is_seen(item_id)]

    def count(self) -> int:
        return len(self.seen)

    def load(self) -> None:
        if not self.path.exists():
            logger.info("No existing state file at %s; starting fresh.", self.path)
            self.seen = {}
            return

        try:
            with self.path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read state file %s (%s); starting fresh.", self.path, exc)
            self.seen = {}
            return

        if not isinstance(payload, dict):
            logger.warning("Invalid state file format; starting fresh.")
            self.seen = {}
            return

        raw_seen = payload.get("seen", {})
        if not isinstance(raw_seen, dict):
            logger.warning("Invalid 'seen' map in state file; starting fresh.")
            self.seen = {}
            return

        self.seen = {str(key): str(value) for key, value in raw_seen.items()}
        logger.info("Loaded %d seen listing ID(s) from %s.", len(self.seen), self.path)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": STATE_VERSION,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "seen": self.seen,
        }
        temp_path = self.path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_path, self.path)
        logger.debug("Saved state with %d seen listing ID(s).", len(self.seen))

    def prune(self, max_entries: int | None = None) -> int:
        """Remove oldest entries when state grows beyond max_entries."""
        limit = max_entries if max_entries is not None else self.max_entries
        if len(self.seen) <= limit:
            return 0

        sorted_items = sorted(self.seen.items(), key=lambda item: item[1])
        remove_count = len(self.seen) - limit
        for item_id, _ in sorted_items[:remove_count]:
            del self.seen[item_id]

        logger.info("Pruned %d old seen listing ID(s).", remove_count)
        return remove_count
