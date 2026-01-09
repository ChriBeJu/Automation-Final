from __future__ import annotations

from automation_hub.adb.adb_client import AdbClient
from automation_hub.config import Config
from automation_hub.logging_utils import get_logger
from automation_hub.models import ActionResult, Event
from automation_hub.pipeline.pipeline import wrap_action_result
from automation_hub.utils.sms_utils import format_whatsapp_sms, split_sms


class SmsSenderAction:
    name = "send_sms"

    def __init__(self, adb_client: AdbClient, config: Config) -> None:
        self.adb_client = adb_client
        self.config = config
        self.logger = get_logger("automation_hub.action.sms")

    def execute(self, event: Event) -> list[Event]:
        if event.event_type != "wa_notification":
            return []
        if not self.config.sms_forward_number:
            self.logger.warning("SMS forward number not configured; skipping WhatsApp forward")
            return []
        sender = str(event.payload.get("sender") or "WhatsApp")
        timestamp = str(event.payload.get("timestamp") or "")
        content = str(event.payload.get("content") or "")
        message = format_whatsapp_sms(sender, timestamp, content)
        segments = split_sms(message, self.config.max_sms_len, self.config.sms_split_len)
        results: list[Event] = []
        for segment in segments:
            try:
                self.adb_client.send_sms(self.config.sms_forward_number, segment)
                result = ActionResult(
                    action_name="send_sms",
                    status="success",
                    details={"message": segment},
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Failed to send SMS")
                result = ActionResult(
                    action_name="send_sms",
                    status="error",
                    details={"error": str(exc), "message": segment},
                )
            results.append(wrap_action_result(event, result))
        return results
