"""Offline tests for rotating rule batches."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import BuyRule
from src.rule_batch import RuleBatchManager


def _rules(count: int) -> list[BuyRule]:
    return [BuyRule(keyword=f"rule-{index}", max_price=10.0) for index in range(count)]


def test_full_scan_when_rules_per_run_zero() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = RuleBatchManager(Path(tmp) / "batch.json", rules_per_run=0)
        all_rules = _rules(5)
        selection = manager.select_rules(all_rules)
        assert len(selection.rules) == 5
        assert selection.is_full_scan
        manager.advance(5, 5)
        assert not (Path(tmp) / "batch.json").exists() or manager._load_offset() == 0


def test_rotating_batches_wrap_around() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "batch.json"
        manager = RuleBatchManager(path, rules_per_run=3)
        all_rules = _rules(7)

        first = manager.select_rules(all_rules)
        assert [rule.keyword for rule in first.rules] == ["rule-0", "rule-1", "rule-2"]
        manager.advance(len(first.rules), first.total_rules)

        second = manager.select_rules(all_rules)
        assert [rule.keyword for rule in second.rules] == ["rule-3", "rule-4", "rule-5"]
        manager.advance(len(second.rules), second.total_rules)

        third = manager.select_rules(all_rules)
        assert [rule.keyword for rule in third.rules] == ["rule-6", "rule-0", "rule-1"]
        manager.advance(len(third.rules), third.total_rules)

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["next_rule_index"] == 2


def main() -> int:
    test_full_scan_when_rules_per_run_zero()
    test_rotating_batches_wrap_around()
    print("Rule batch tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
