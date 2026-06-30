"""Rotating rule batches for short scheduled scans."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.config_loader import BuyRule

logger = logging.getLogger(__name__)

STATE_VERSION = 1


@dataclass(frozen=True)
class RuleBatchSelection:
    """A slice of buy rules selected for one scan run."""

    rules: list[BuyRule]
    start_index: int
    total_rules: int
    batch_size: int

    @property
    def is_full_scan(self) -> bool:
        return self.batch_size >= self.total_rules


class RuleBatchManager:
    """Rotate through buy rules across scheduled --once runs."""

    def __init__(self, path: Path, rules_per_run: int) -> None:
        self._path = path
        self._rules_per_run = rules_per_run

    def select_rules(self, all_rules: list[BuyRule]) -> RuleBatchSelection:
        total = len(all_rules)
        if total == 0:
            return RuleBatchSelection([], 0, 0, 0)

        batch_size = total if self._rules_per_run <= 0 else min(self._rules_per_run, total)
        if batch_size >= total:
            return RuleBatchSelection(list(all_rules), 0, total, total)

        start = self._load_offset() % total
        end = start + batch_size
        if end <= total:
            batch = all_rules[start:end]
        else:
            batch = all_rules[start:] + all_rules[: end - total]

        return RuleBatchSelection(batch, start, total, batch_size)

    def advance(self, rules_scanned: int, total_rules: int) -> None:
        if self._rules_per_run <= 0 or rules_scanned <= 0 or total_rules <= 0:
            return
        if self._rules_per_run >= total_rules:
            return

        current = self._load_offset() % total_rules
        next_offset = (current + rules_scanned) % total_rules
        self._save_offset(next_offset)
        logger.debug(
            "Rule batch offset advanced %d -> %d (total rules=%d).",
            current,
            next_offset,
            total_rules,
        )

    def _load_offset(self) -> int:
        if not self._path.exists():
            return 0

        try:
            with self._path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read rule batch state at %s: %s", self._path, exc)
            return 0

        if not isinstance(data, dict):
            return 0
        if data.get("version") != STATE_VERSION:
            return 0

        offset = data.get("next_rule_index", 0)
        try:
            return max(0, int(offset))
        except (TypeError, ValueError):
            return 0

    def _save_offset(self, offset: int) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": STATE_VERSION, "next_rule_index": offset}
        temp_path = self._path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        temp_path.replace(self._path)
