from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from automation_hub.logging_utils import get_logger


@dataclass(frozen=True)
class AdbNotification:
    title: str
    text: str
    timestamp: datetime


@dataclass(frozen=True)
class AdbSms:
    message_id: str
    sender: str
    body: str
    timestamp: datetime


class AdbClient:
    def __init__(self, adb_path: str, device_id: str | None = None) -> None:
        self.adb_path = adb_path
        self.device_id = device_id
        self.logger = get_logger("automation_hub.adb")

    def _base_command(self) -> list[str]:
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        return cmd

    def run(self, args: Iterable[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
        cmd = [*self._base_command(), *args]
        self.logger.debug("Running adb command: %s", " ".join(cmd))
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def shell(self, command: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
        return self.run(["shell", command], timeout=timeout)

    def shell_args(self, args: Iterable[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
        return self.run(["shell", *args], timeout=timeout)

    def list_devices(self) -> list[str]:
        proc = self.run(["devices"]) 
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "adb devices failed")
        lines = [line for line in proc.stdout.splitlines() if "\tdevice" in line]
        return [line.split("\t", 1)[0] for line in lines]

    def fetch_whatsapp_notifications(self) -> list[AdbNotification]:
        proc = self.shell("dumpsys notification --noredact")
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "dumpsys notification failed")
        return _parse_whatsapp_notifications(proc.stdout)

    def fetch_sms_inbox(self) -> list[AdbSms]:
        proc = self.shell(
            "content query --uri content://sms/inbox --projection _id,address,date,body --sort \"date DESC\""
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "content query failed")
        return _parse_sms_inbox(proc.stdout)

    def send_sms(self, number: str, body: str) -> None:
        args = [
            "am",
            "start",
            "-a",
            "android.intent.action.SENDTO",
            "-d",
            f"smsto:{number}",
            "--es",
            "sms_body",
            body,
            "--ez",
            "exit_on_sent",
            "true",
        ]
        proc = self.shell_args(args, timeout=20)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "SMS send failed")


_WHATSAPP_RECORD = re.compile(r"NotificationRecord\(.*?pkg=com\.whatsapp")
_POST_TIME = re.compile(r"postTime=(\d+)")


def _parse_whatsapp_notifications(output: str) -> list[AdbNotification]:
    notifications: list[AdbNotification] = []
    current: dict[str, str | datetime] = {}
    in_record = False
    for line in output.splitlines():
        if _WHATSAPP_RECORD.search(line):
            if current:
                notifications.append(_build_notification(current))
                current = {}
            in_record = True
            match = _POST_TIME.search(line)
            if match:
                current["timestamp"] = datetime.utcfromtimestamp(int(match.group(1)) / 1000)
            continue
        if in_record and line.strip().startswith("NotificationRecord("):
            if current:
                notifications.append(_build_notification(current))
                current = {}
            continue
        if not in_record:
            continue
        if "android.title" in line:
            current["title"] = _extract_value(line)
        if "android.text" in line:
            current["text"] = _extract_value(line)
        if line.strip() == "" and current:
            notifications.append(_build_notification(current))
            current = {}
            in_record = False
    if current:
        notifications.append(_build_notification(current))
    return [item for item in notifications if item.text]


def _build_notification(data: dict[str, str | datetime]) -> AdbNotification:
    title = str(data.get("title") or "WhatsApp")
    text = str(data.get("text") or "")
    timestamp = data.get("timestamp")
    if not isinstance(timestamp, datetime):
        timestamp = datetime.utcnow()
    return AdbNotification(title=title, text=text, timestamp=timestamp)


def _extract_value(line: str) -> str:
    if "=" in line:
        return line.split("=", 1)[1].strip()
    return line.split(":", 1)[1].strip() if ":" in line else line.strip()


def _parse_sms_inbox(output: str) -> list[AdbSms]:
    messages: list[AdbSms] = []
    for line in output.splitlines():
        if "_id=" not in line:
            continue
        fields = dict(item.split("=", 1) for item in line.split() if "=" in item)
        message_id = fields.get("_id")
        if not message_id:
            continue
        sender = fields.get("address", "")
        body = fields.get("body", "")
        date_raw = fields.get("date")
        timestamp = datetime.utcfromtimestamp(int(date_raw) / 1000) if date_raw else datetime.utcnow()
        messages.append(
            AdbSms(message_id=message_id, sender=sender, body=body, timestamp=timestamp)
        )
    return messages
