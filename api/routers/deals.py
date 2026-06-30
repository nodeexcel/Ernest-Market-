"""Deal results and export endpoints."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

from api.dependencies import get_settings
from api.schemas import DealRow, DealsPage, ExportStatusResponse
from api.services.sheets_reader import SheetsReader, SheetsReaderError

router = APIRouter(prefix="/deals", tags=["deals"])


def _filter_deals(
    deals: list[dict],
    *,
    search: str,
    marketplace: str,
    keyword: str,
) -> list[dict]:
    result = deals
    if marketplace and marketplace.lower() != "all":
        result = [d for d in result if d["marketplace"].lower() == marketplace.lower()]
    if keyword:
        result = [d for d in result if keyword.lower() in d["keyword"].lower()]
    if search:
        needle = search.lower()
        result = [
            d
            for d in result
            if needle in d["title"].lower()
            or needle in d["keyword"].lower()
            or needle in d["item_id"].lower()
        ]
    return result


@router.get("/export-status", response_model=ExportStatusResponse)
def export_status() -> ExportStatusResponse:
    settings = get_settings()
    try:
        reader = SheetsReader(settings)
        status = reader.export_status()
        return ExportStatusResponse(**status)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("", response_model=DealsPage)
def list_deals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    search: str = Query(""),
    marketplace: str = Query("all"),
    keyword: str = Query(""),
) -> DealsPage:
    settings = get_settings()
    try:
        reader = SheetsReader(settings)
        deals = reader.fetch_all_deals()
    except SheetsReaderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filtered = _filter_deals(deals, search=search, marketplace=marketplace, keyword=keyword)
    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    page_items = filtered[start : start + page_size]

    return DealsPage(
        items=[DealRow(**item) for item in page_items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/export")
def export_deals(format: str = Query("xlsx", pattern="^(xlsx|csv)$")):
    settings = get_settings()
    try:
        reader = SheetsReader(settings)
        deals = reader.fetch_all_deals()
    except SheetsReaderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not deals:
        raise HTTPException(status_code=404, detail="No deals available to export.")

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
                "Content-Disposition": f'attachment; filename="ernest-market-deals_{timestamp}.csv"'
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

    xlsx_buffer = io.BytesIO()
    workbook.save(xlsx_buffer)
    xlsx_buffer.seek(0)

    return StreamingResponse(
        xlsx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="ernest-market-deals_{timestamp}.xlsx"'
        },
    )
