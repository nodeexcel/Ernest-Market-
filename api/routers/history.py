"""Scan history endpoints."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

from api.dependencies import get_history_store, get_settings
from api.schemas import HistoryEntry, ScanStatsResponse
from api.services.sheets_reader import SheetsReader, SheetsReaderError

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryEntry])
def list_history() -> list[HistoryEntry]:
    entries = get_history_store().list_entries()
    result: list[HistoryEntry] = []
    for entry in entries:
        stats = ScanStatsResponse(**entry.stats) if entry.stats else None
        result.append(
            HistoryEntry(
                id=entry.id,
                started_at=entry.started_at,
                completed_at=entry.completed_at,
                status=entry.status,
                mode=entry.mode,
                stats=stats,
                error=entry.error,
            )
        )
    return result


@router.get("/{entry_id}/export")
def export_history_snapshot(entry_id: str, format: str = "xlsx"):
    entry = get_history_store().get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="History entry not found.")

    settings = get_settings()
    try:
        reader = SheetsReader(settings)
        deals = reader.fetch_all_deals()
    except SheetsReaderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    headers = [
        "Timestamp (UTC)",
        "Marketplace",
        "Keyword",
        "Title",
        "Price",
        "Currency",
        "URL",
        "Item ID",
        "Condition",
    ]

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for deal in deals:
            writer.writerow(
                [
                    deal["timestamp"],
                    deal["marketplace"],
                    deal["keyword"],
                    deal["title"],
                    deal["price"],
                    deal["currency"],
                    deal["url"],
                    deal["item_id"],
                    deal["condition"],
                ]
            )
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="ernest-market-history_{entry_id[:8]}_{timestamp}.csv"'
                )
            },
        )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Deals"
    sheet.append(headers)
    for deal in deals:
        sheet.append(
            [
                deal["timestamp"],
                deal["marketplace"],
                deal["keyword"],
                deal["title"],
                deal["price"],
                deal["currency"],
                deal["url"],
                deal["item_id"],
                deal["condition"],
            ]
        )

    meta = workbook.create_sheet("Run Info")
    meta.append(["Field", "Value"])
    meta.append(["Run ID", entry.id])
    meta.append(["Started", entry.started_at])
    meta.append(["Completed", entry.completed_at or ""])
    meta.append(["Status", entry.status])
    meta.append(["Mode", entry.mode])
    if entry.stats:
        for key, value in entry.stats.items():
            meta.append([key, value])

    xlsx_buffer = io.BytesIO()
    workbook.save(xlsx_buffer)
    xlsx_buffer.seek(0)

    return StreamingResponse(
        xlsx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f'attachment; filename="ernest-market-history_{entry_id[:8]}_{timestamp}.xlsx"'
            )
        },
    )
