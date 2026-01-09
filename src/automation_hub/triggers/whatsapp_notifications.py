from __future__ import annotations

from datetime import datetime

from automation_hub.adb.adb_client import AdbClient
from automation_hub.logging_utils import get_logger
from automation_hub.models import Event
from automation_hub.utils.hashing import stable_hash


class WhatsAppNotificationTrigger:
    name = "whatsapp_notifications"

    def __init__(self, adb_client: AdbClient) -> None:
        self.adb_client = adb_client
        self.logger = get_logger("automation_hub.trigger.whatsapp")

    def poll(self) -> list[Event]:
        notifications = self.adb_client.fetch_whatsapp_notifications()
        events: list[Event] = []
        for notification in notifications:
            bucket = int(notification.timestamp.timestamp() // 60)
            dedupe_key = stable_hash(
                f"wa:{notification.title}:{notification.text}:{bucket}"
            )
            events.append(
                Event(
                    event_type="wa_notification",
                    source="adb",
                    payload={
                        "sender": notification.title,
                        "content": notification.text,
                        "timestamp": notification.timestamp.isoformat() + "Z",
                    },
                    occurred_at=datetime.utcnow(),
                    dedupe_key=dedupe_key,
                )
            )
        return events
