from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    name: str
    topic: str | None = None


def parse_command(text: str) -> Command | None:
    if not text:
        return None
    raw = text.strip()
    compact = re.sub(r"\s+", "", raw)
    if compact in {"!", "n", "N"}:
        return Command(name="NEWS")
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", raw).strip().upper()
    if not normalized:
        return None
    parts = normalized.split()
    name = parts[0]
    topic = " ".join(parts[1:]) if len(parts) > 1 else None
    if name in {"NEWS", "INFO", "HELP"}:
        return Command(name=name, topic=topic)
    return None
