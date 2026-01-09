from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)"
        )
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS processed (key TEXT PRIMARY KEY)"
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def get(self, key: str) -> Any:
        cursor = self._connection.execute("SELECT value FROM kv WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def set(self, key: str, value: Any) -> None:
        payload = json.dumps(value)
        self._connection.execute(
            "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)", (key, payload)
        )
        self._connection.commit()

    def has_processed(self, key: str) -> bool:
        cursor = self._connection.execute("SELECT 1 FROM processed WHERE key = ?", (key,))
        return cursor.fetchone() is not None

    def mark_processed(self, key: str) -> None:
        self._connection.execute("INSERT OR IGNORE INTO processed (key) VALUES (?)", (key,))
        self._connection.commit()
