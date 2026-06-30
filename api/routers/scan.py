"""Scan control and live status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.dependencies import get_scan_runner
from api.schemas import LogLine, MessageResponse, ScanStatusResponse, StartScanRequest

router = APIRouter(prefix="/scan", tags=["scan"])


@router.get("/status", response_model=ScanStatusResponse)
def get_scan_status() -> ScanStatusResponse:
    return ScanStatusResponse(**get_scan_runner().get_status())


@router.post("/start", response_model=MessageResponse)
def start_scan(body: StartScanRequest) -> MessageResponse:
    runner = get_scan_runner()
    started = runner.start(mode=body.mode)
    if not started:
        raise HTTPException(status_code=409, detail="A scan is already running.")
    label = "dry-run" if body.mode == "dry_run" else "full"
    return MessageResponse(
        message=f"{label.capitalize()} scan started.",
        detail={"mode": body.mode},
    )


@router.get("/logs", response_model=list[LogLine])
def get_scan_logs(lines: int = 80) -> list[LogLine]:
    capped = max(10, min(lines, 200))
    logs = get_scan_runner().get_recent_logs(max_lines=capped)
    return [LogLine(**entry) for entry in logs]
