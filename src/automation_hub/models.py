from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Event:
    event_type: str
    source: str
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    dedupe_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["occurred_at"] = self.occurred_at.isoformat() + "Z"
        return data


@dataclass(frozen=True)
class ActionResult:
    action_name: str
    status: str
    details: dict[str, Any]

    def to_event_payload(self) -> dict[str, Any]:
        return {"action": self.action_name, "status": self.status, **self.details}
