"""FastAPI application entry point for the Ernest Market dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import config, dashboard, deals, history, scan

app = FastAPI(
    title="Ernest Market Dashboard API",
    description="Thin HTTP wrapper around the existing Ernest Market scan pipeline.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:20156",
        "http://127.0.0.1:20156",
        "http://116.202.210.102:20156",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api")
app.include_router(scan.router, prefix="/api")
app.include_router(deals.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(history.router, prefix="/api")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
