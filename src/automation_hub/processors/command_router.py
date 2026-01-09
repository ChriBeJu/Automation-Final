from __future__ import annotations

from typing import Callable

from automation_hub.adb.adb_client import AdbClient
from automation_hub.config import Config
from automation_hub.logging_utils import get_logger
from automation_hub.models import ActionResult, Event
from automation_hub.pipeline.pipeline import wrap_action_result
from automation_hub.processors.command_parser import Command, parse_command
from automation_hub.utils.sms_utils import split_sms


Handler = Callable[[Command], str]


def _help_handler(_: Command) -> str:
    return "Commands: HELP, NEWS <topic>, INFO <topic>, N, !"


def _stub_handler(command: Command) -> str:
    return f"Received {command.name} request. News module not yet enabled."


class SmsCommandRouterAction:
    name = "sms_command_router"

    def __init__(self, adb_client: AdbClient, config: Config) -> None:
        self.adb_client = adb_client
        self.config = config
        self.logger = get_logger("automation_hub.action.sms_commands")
        self.handlers: dict[str, Handler] = {
            "HELP": _help_handler,
            "NEWS": _stub_handler,
            "INFO": _stub_handler,
        }

    def execute(self, event: Event) -> list[Event]:
        if event.event_type != "sms_inbound":
            return []
        command = parse_command(str(event.payload.get("body") or ""))
        if not command:
            return []
        handler = self.handlers.get(command.name)
        if not handler:
            return []
        response = handler(command)
        segments = split_sms(response, self.config.max_sms_len, self.config.sms_split_len)
        results: list[Event] = []
        sender = str(event.payload.get("sender") or "")
        for segment in segments:
            try:
                self.adb_client.send_sms(sender, segment)
                result = ActionResult(
                    action_name="sms_command_reply",
                    status="success",
                    details={"message": segment},
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Failed to send SMS command reply")
                result = ActionResult(
                    action_name="sms_command_reply",
                    status="error",
                    details={"error": str(exc), "message": segment},
                )
            results.append(wrap_action_result(event, result))
        return results
