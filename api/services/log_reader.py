"""Read and parse application log files."""

from __future__ import annotations

import re
from pathlib import Path

_LOG_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"
    r"\s+-\s+(?P<logger>[\w.]+)\s+-\s+(?P<level>\w+)\s+-\s+(?P<message>.+)$"
)
_SCANNING_RULE_RE = re.compile(
    r"Scanning rule (\d+)/(\d+) \[(?P<marketplace>\w+)\]: keyword='(?P<keyword>[^']+)'"
)
_SCAN_COMPLETE_RE = re.compile(
    r"Scan complete — rules=(\d+)/(\d+) fetched=(\d+) qualified=(\d+) "
    r"skipped_seen=(\d+) alerts=(\d+) capped=(\d+) errors=(\d+)"
)


def tail_log(path: Path, *, max_lines: int = 100) -> list[dict[str, str | None]]:
    if not path.exists():
        return []

    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return []

    parsed: list[dict[str, str | None]] = []
    for raw in lines[-max_lines:]:
        line = raw.rstrip("\n")
        match = _LOG_LINE_RE.match(line)
        if match:
            parsed.append(
                {
                    "timestamp": match.group("timestamp"),
                    "level": match.group("level"),
                    "message": match.group("message"),
                }
            )
        elif line.strip():
            parsed.append({"timestamp": None, "level": None, "message": line})
    return parsed


def parse_scanning_progress(message: str) -> tuple[int, int, str] | None:
    match = _SCANNING_RULE_RE.search(message)
    if not match:
        return None
    current = int(match.group(1))
    total = int(match.group(2))
    step = (
        f"Searching {match.group('marketplace')} for "
        f"\"{match.group('keyword')}\""
    )
    return current, total, step


def parse_scan_complete(message: str) -> dict[str, int] | None:
    match = _SCAN_COMPLETE_RE.search(message)
    if not match:
        return None
    return {
        "rules_scanned": int(match.group(1)),
        "rules_total": int(match.group(2)),
        "listings_fetched": int(match.group(3)),
        "listings_qualified": int(match.group(4)),
        "listings_skipped_seen": int(match.group(5)),
        "alerts_sent": int(match.group(6)),
        "alerts_capped": int(match.group(7)),
        "errors": int(match.group(8)),
    }
