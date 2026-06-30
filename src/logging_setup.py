"""Centralized logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.settings import Settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
MAX_LOG_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 5


def configure_logging(settings: Settings) -> None:
    """Configure console and rotating file logging."""
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.log_dir / "app.log"

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level)

    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
