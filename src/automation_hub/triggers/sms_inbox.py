from __future__ import annotations

from datetime import datetime

from automation_hub.adb.adb_client import AdbClient
from automation_hub.logging_utils import get_logger
from automation_hub.models import Event


class SmsInboxTrigger:
    name = "sms_inbox"

    def __init__(self, adb_client: AdbClient, last_id_key: str = "sms_last_id") -> None:
        self.adb_client = adb_client
        self.last_id_key = last_id_key
        self.logger = get_logger("automation_hub.trigger.sms")

    def poll(self) -> list[Event]:
        messages = self.adb_client.fetch_sms_inbox()
        events: list[Event] = []
        for message in messages:
            events.append(
                Event(
                    event_type="sms_inbound",
                    source="adb",
                    payload={
                        "sms_id": message.message_id,
                        "sender": message.sender,
                        "body": message.body,
                        "timestamp": message.timestamp.isoformat() + "Z",
                    },
                    occurred_at=datetime.utcnow(),
                    dedupe_key=f"sms:{message.message_id}",
                )
            )
        return events
