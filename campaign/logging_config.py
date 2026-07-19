"""Rotating log file configuration for application, campaign, and error logs."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def _rotating_handler(filename: str, level: int) -> RotatingFileHandler:
    LOG_DIR.mkdir(exist_ok=True)
    handler = RotatingFileHandler(LOG_DIR / filename, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    return handler


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(_rotating_handler("application.log", logging.INFO))
    root.addHandler(_rotating_handler("error.log", logging.ERROR))

    campaign_logger = logging.getLogger("campaign_sender")
    campaign_logger.addHandler(_rotating_handler("campaign.log", logging.INFO))
