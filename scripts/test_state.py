"""Offline tests for deduplication state persistence."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.state import SeenState


def run_tests() -> int:
    failed = 0

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "seen_listings.json"
        state = SeenState(path=path, max_entries=3)

        state.load()
        if state.count() == 0:
            print("[PASS] fresh state starts empty")
        else:
            print("[FAIL] fresh state should be empty")
            failed += 1

        state.mark_seen("v1|111")
        state.mark_seen("v1|222")
        state.save()

        reloaded = SeenState(path=path)
        reloaded.load()
        if reloaded.is_seen("v1|111") and reloaded.is_seen("v1|222"):
            print("[PASS] state persists across save/load")
        else:
            print("[FAIL] state did not persist")
            failed += 1

        reloaded.mark_seen("v1|333")
        reloaded.mark_seen("v1|444")
        pruned = reloaded.prune(max_entries=3)
        if pruned == 1 and reloaded.count() == 3:
            print("[PASS] prune keeps newest entries")
        else:
            print(f"[FAIL] prune expected removed=1 count=3, got removed={pruned} count={reloaded.count()}")
            failed += 1

        fresh = SeenState(path=path)
        fresh.load()
        fresh.seen = {"v1|111": "2026-01-01T00:00:00+00:00"}
        unseen = fresh.unseen_from(["v1|111", "v1|999"])
        if unseen == ["v1|999"]:
            print("[PASS] unseen_from filters correctly")
        else:
            print(f"[FAIL] unseen_from unexpected result: {unseen}")
            failed += 1

        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("version") == 1 and isinstance(payload.get("seen"), dict):
            print("[PASS] state file JSON structure valid")
        else:
            print("[FAIL] invalid state file structure")
            failed += 1

    print()
    if failed:
        print(f"{failed} test(s) failed.")
        return 1
    print("All state tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
