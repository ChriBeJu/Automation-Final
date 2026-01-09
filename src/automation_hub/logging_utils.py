from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _resolve_level(value: str | None, default: int) -> int:
    if not value:
        return default
    name = value.strip().upper()
    return logging._nameToLevel.get(name, default)


def configure_logging(log_dir: Path, log_level: str = "INFO", console_level: str | None = None) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "automation_hub.log"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [corr=%(correlation_id)s] %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)

    resolved_log_level = _resolve_level(log_level, logging.INFO)
    resolved_console_level = _resolve_level(console_level or log_level, resolved_log_level)
    handler.setLevel(resolved_console_level)
    file_handler.setLevel(resolved_log_level)

    logging.basicConfig(level=logging.DEBUG, handlers=[handler, file_handler])


def get_logger(name: str, correlation_id: str | None = None) -> logging.LoggerAdapter:
    base_logger = logging.getLogger(name)
    return logging.LoggerAdapter(base_logger, {"correlation_id": correlation_id or "-"})
