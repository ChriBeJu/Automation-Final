from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "automation_hub.log"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [corr=%(correlation_id)s] %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[handler, file_handler])


def get_logger(name: str, correlation_id: str | None = None) -> logging.LoggerAdapter:
    base_logger = logging.getLogger(name)
    return logging.LoggerAdapter(base_logger, {"correlation_id": correlation_id or "-"})
