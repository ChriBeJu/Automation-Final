from __future__ import annotations

from math import ceil


def split_sms(message: str, max_len: int = 160, split_len: int = 153) -> list[str]:
    if len(message) <= max_len:
        return [message]
    parts = [message[i : i + split_len] for i in range(0, len(message), split_len)]
    total = len(parts)
    return [f"{index + 1}/{total} {part}" for index, part in enumerate(parts)]


def format_whatsapp_sms(sender: str, timestamp: str, content: str) -> str:
    return f"[WA] {sender} {timestamp}\n{content}".strip()
