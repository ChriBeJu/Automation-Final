from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

TRUE_VALUES = {"1", "true", "yes", "on"}


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_news_feeds(value: str | None) -> list[tuple[str, str]]:
    if not value:
        return []
    feeds: list[tuple[str, str]] = []
    for entry in value.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        if "|" in entry:
            name, url = entry.split("|", 1)
            name = name.strip() or url.strip()
            feeds.append((name, url.strip()))
        else:
            feeds.append((entry, entry))
    return feeds


@dataclass(frozen=True)
class Config:
    adb_path: str
    device_id: str | None
    sms_forward_number: str
    allowed_sms_senders: list[str]
    poll_interval_sec: float
    enable_sms_commands: bool
    enable_whatsapp_forwarding: bool
    enable_llm: bool
    enable_whatsapp_polling: bool
    event_store_path: Path
    state_store_path: Path
    log_dir: Path
    log_level: str
    console_log_level: str
    max_sms_len: int
    sms_split_len: int
    news_feeds: list[tuple[str, str]]
    news_max_items: int
    news_timeout_sec: int
    ollama_url: str
    ollama_model: str
    ollama_timeout_sec: int

    @classmethod
    def load(cls, env_path: Path) -> "Config":
        values = _load_env_file(env_path)
        adb_path = values.get("ADB_PATH", "adb")
        device_id = values.get("ADB_DEVICE_ID") or None
        sms_forward_number = values.get("SMS_FORWARD_NUMBER", "")
        allowed_sms_senders = _parse_list(values.get("ALLOWED_SMS_SENDERS"))
        poll_interval_sec = float(values.get("POLL_INTERVAL_SEC", "5"))
        enable_sms_commands = _parse_bool(values.get("ENABLE_SMS_COMMANDS", "true"), True)
        enable_whatsapp_forwarding = _parse_bool(
            values.get("ENABLE_WHATSAPP_FORWARDING", "true"), True
        )
        enable_llm = _parse_bool(values.get("ENABLE_LLM", "false"), False)
        enable_whatsapp_polling = _parse_bool(
            values.get("ENABLE_WHATSAPP_POLLING", "true"), True
        )
        event_store_path = Path(values.get("EVENT_STORE_PATH", "data/events.jsonl"))
        state_store_path = Path(values.get("STATE_STORE_PATH", "data/state.db"))
        log_dir = Path(values.get("LOG_DIR", "logs"))
        log_level = values.get("LOG_LEVEL", "INFO")
        console_log_level = values.get("CONSOLE_LOG_LEVEL", log_level)
        max_sms_len = int(values.get("MAX_SMS_LEN", "160"))
        sms_split_len = int(values.get("SMS_SPLIT_LEN", "153"))
        news_feeds = _parse_news_feeds(values.get("NEWS_FEEDS"))
        news_max_items = int(values.get("NEWS_MAX_ITEMS", "10"))
        news_timeout_sec = int(values.get("NEWS_TIMEOUT_SEC", "12"))
        ollama_url = values.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        ollama_model = values.get("OLLAMA_MODEL", "llama3.1:8b")
        ollama_timeout_sec = int(values.get("OLLAMA_TIMEOUT_SEC", "30"))
        return cls(
            adb_path=adb_path,
            device_id=device_id,
            sms_forward_number=sms_forward_number,
            allowed_sms_senders=allowed_sms_senders,
            poll_interval_sec=poll_interval_sec,
            enable_sms_commands=enable_sms_commands,
            enable_whatsapp_forwarding=enable_whatsapp_forwarding,
            enable_llm=enable_llm,
            enable_whatsapp_polling=enable_whatsapp_polling,
            event_store_path=event_store_path,
            state_store_path=state_store_path,
            log_dir=log_dir,
            log_level=log_level,
            console_log_level=console_log_level,
            max_sms_len=max_sms_len,
            sms_split_len=sms_split_len,
            news_feeds=news_feeds,
            news_max_items=news_max_items,
            news_timeout_sec=news_timeout_sec,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
            ollama_timeout_sec=ollama_timeout_sec,
        )


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_config() -> Config:
    env_path = Path(os.environ.get("AUTOMATION_HUB_CONFIG", "config.local.env"))
    return Config.load(env_path)


def ensure_directories(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
