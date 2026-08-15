"""Rotating log file configuration for application, campaign, and error logs."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def _rotating_handler(log_dir: Path, filename: str, level: int) -> RotatingFileHandler:
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(log_dir / filename, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    return handler


def configure_logging(log_dir: Path | str = "logs") -> None:
    log_dir = Path(log_dir)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(_rotating_handler(log_dir, "application.log", logging.INFO))
    root.addHandler(_rotating_handler(log_dir, "error.log", logging.ERROR))

    campaign_logger = logging.getLogger("campaign_sender")
    campaign_logger.addHandler(_rotating_handler(log_dir, "campaign.log", logging.INFO))
