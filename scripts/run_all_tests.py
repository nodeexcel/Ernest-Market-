"""Run all Ernest Market tests and report pass/fail status."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
SECRETS_PATH = ROOT / "secrets" / "google-credentials.json"

PLACEHOLDER_MARKERS = {
    "SCRAPERAPI_KEY": {"your_scraperapi_key"},
    "EBAY_CLIENT_ID": {"your_ebay_client_id", "your_client_id"},
    "EBAY_CLIENT_SECRET": {"your_ebay_client_secret", "your_client_secret"},
    "TELEGRAM_BOT_TOKEN": {"123456789:abcdefghijklmnopqrstuvwxyz"},
    "TELEGRAM_CHANNEL_ID": {"-1001234567890"},
    "GOOGLE_SHEETS_ID": {"your_google_sheet_id_from_url", "your_sheet_id"},
}


def _is_placeholder(key: str, value: str) -> bool:
    if not value:
        return True
    placeholders = PLACEHOLDER_MARKERS.get(key, set())
    return value.lower() in placeholders or value.startswith("your_")


def _check_credential(report: TestReport, key: str, value: str) -> None:
    if _is_placeholder(key, value):
        report.add(
            CheckResult(
                name=f"{key} configured",
                passed=False,
                detail=f"{key} is empty or still a placeholder.",
                manual_action=f"Set {key} in `.env` (see SETUP.md).",
            )
        )
    else:
        report.add(CheckResult(f"{key} configured", True, "Real value detected."))


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    manual_action: str | None = None


@dataclass
class TestReport:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)

    @property
    def passed(self) -> int:
        return sum(1 for check in self.checks if check.passed)

    @property
    def failed(self) -> int:
        return sum(1 for check in self.checks if not check.passed)


def _load_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _check_env_file(report: TestReport) -> None:
    if not ENV_PATH.exists():
        report.add(
            CheckResult(
                name="`.env` file exists",
                passed=False,
                detail="Missing `.env` file.",
                manual_action="Copy `.env.example` to `.env` and fill in real credentials.",
            )
        )
        return

    report.add(CheckResult("`.env` file exists", True, "Found `.env`."))
    values = _load_env_values()
    backend = values.get("EBAY_BACKEND", "official").strip().lower()

    report.add(
        CheckResult(
            name="EBAY_BACKEND configured",
            passed=backend in {"official", "scraperapi"},
            detail=f"EBAY_BACKEND={backend!r}",
            manual_action="Set EBAY_BACKEND to `official` or `scraperapi`.",
        )
    )

    if backend == "scraperapi":
        _check_credential(report, "SCRAPERAPI_KEY", values.get("SCRAPERAPI_KEY", ""))
    else:
        _check_credential(report, "EBAY_CLIENT_ID", values.get("EBAY_CLIENT_ID", ""))
        _check_credential(report, "EBAY_CLIENT_SECRET", values.get("EBAY_CLIENT_SECRET", ""))

    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL_ID", "GOOGLE_SHEETS_ID"):
        _check_credential(report, key, values.get(key, ""))

    ebay_env = values.get("EBAY_ENV", "production").lower()
    if ebay_env in {"sandbox", "production"}:
        report.add(
            CheckResult(
                name="EBAY_ENV valid",
                passed=True,
                detail=f"EBAY_ENV={ebay_env} (keys must match this environment in eBay Developer Portal).",
            )
        )
    else:
        report.add(
            CheckResult(
                name="EBAY_ENV valid",
                passed=False,
                detail=f"Invalid EBAY_ENV={ebay_env!r}.",
                manual_action="Set EBAY_ENV to `sandbox` or `production`.",
            )
        )


def _check_google_credentials(report: TestReport) -> None:
    if SECRETS_PATH.exists():
        report.add(CheckResult("Google credentials JSON", True, str(SECRETS_PATH)))
    else:
        report.add(
            CheckResult(
                name="Google credentials JSON",
                passed=False,
                detail=f"Missing {SECRETS_PATH}",
                manual_action="Download service account JSON from Google Cloud and save as secrets/google-credentials.json",
            )
        )


def _check_config_yaml(report: TestReport) -> None:
    config_path = ROOT / "config.yaml"
    if config_path.exists():
        report.add(CheckResult("`config.yaml` exists", True, "Found buy rules file."))
    else:
        report.add(
            CheckResult(
                name="`config.yaml` exists",
                passed=False,
                detail="Missing config.yaml.",
                manual_action="Copy config.example.yaml to config.yaml and edit buy rules.",
            )
        )


def _run_script(script: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).strip()
    tail = "\n".join(output.splitlines()[-8:]) if output else "(no output)"
    return result.returncode == 0, tail


def _run_main_check() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).strip()
    tail = "\n".join(output.splitlines()[-8:]) if output else "(no output)"
    return result.returncode == 0, tail


def main() -> int:
    report = TestReport()

    print("=" * 60)
    print("Ernest Market — Full Test Report")
    print("=" * 60)
    print()

    print("--- Pre-flight checks ---")
    _check_env_file(report)
    _check_google_credentials(report)
    _check_config_yaml(report)

    script_tests = [
        ("test_filter.py", "Filter logic (offline)"),
        ("test_state.py", "Dedupe state (offline)"),
        ("test_rule_batch.py", "Rule batch rotation (offline)"),
        ("test_telegram_retry.py", "Telegram 429 parsing (offline)"),
        ("test_mercari_parse.py", "Mercari parser (offline)"),
        ("test_ebay.py", "eBay search live"),
        ("test_mercari.py", "Mercari RapidAPI live"),
        ("test_telegram.py", "Telegram live"),
        ("test_sheets.py", "Google Sheets live"),
    ]

    env_values = _load_env_values()
    mercari_enabled = env_values.get("MERCARI_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    print()
    print("--- Script tests ---")
    for script, label in script_tests:
        if script == "test_mercari.py" and not mercari_enabled:
            report.add(
                CheckResult(
                    label,
                    True,
                    "Skipped — set MERCARI_ENABLED=true and RAPIDAPI_KEY to test.",
                )
            )
            continue
        ok, tail = _run_script(script)
        manual = None
        if not ok and script == "test_ebay.py":
            manual = "Check SCRAPERAPI_KEY (scraperapi) or EBAY_CLIENT_ID/SECRET (official) in .env."
        elif not ok and script == "test_mercari.py":
            manual = (
                "Subscribe at https://rapidapi.com/k19862217/api/mercari-item-search, "
                "set MERCARI_ENABLED=true and RAPIDAPI_KEY in .env."
            )
        elif not ok and script == "test_telegram.py":
            manual = "Create bot via @BotFather, add bot as admin to private channel, set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID."
        elif not ok and script == "test_sheets.py":
            manual = "Create Google service account, download JSON to secrets/, share sheet with service account email."
        report.add(CheckResult(label, ok, tail, manual))

    print()
    print("--- Full connectivity (main.py --check) ---")
    ok, tail = _run_main_check()
    report.add(
        CheckResult(
            "main.py --check (Telegram + Sheets)",
            ok,
            tail,
            None if ok else "Fix Telegram and Google Sheets setup, then re-run.",
        )
    )

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"[{status}] {check.name}")
        if not check.passed:
            print(f"        {check.detail.splitlines()[-1][:120]}")
            if check.manual_action:
                print(f"        -> {check.manual_action}")

    print()
    print(f"Total: {report.passed} passed, {report.failed} failed out of {len(report.checks)} checks.")
    print()

    if report.failed == 0:
        print("All checks passed. Run: python main.py --once")
        return 0

    print("Manual setup required for failed checks. See SETUP.md for step-by-step instructions.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
