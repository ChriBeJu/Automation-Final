from __future__ import annotations

from typing import Callable

from automation_hub.adb.adb_client import AdbClient
from automation_hub.config import Config
from automation_hub.logging_utils import get_logger
from automation_hub.models import ActionResult, Event
from automation_hub.pipeline.pipeline import wrap_action_result
from automation_hub.processors.command_parser import Command, parse_command
from automation_hub.services.news_service import NewsFeed, NewsItem, NewsService
from automation_hub.services.ollama_client import OllamaClient
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
        self.news_service = NewsService(
            feeds=[NewsFeed(name, url) for name, url in config.news_feeds],
            timeout_sec=config.news_timeout_sec,
            max_items=config.news_max_items,
        )
        self.ollama_client = (
            OllamaClient(config.ollama_url, config.ollama_model, config.ollama_timeout_sec)
            if config.enable_llm
            else None
        )
        self.handlers: dict[str, Handler] = {
            "HELP": _help_handler,
            "NEWS": self._news_handler,
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

    def _news_handler(self, command: Command) -> str:
        items = self.news_service.fetch_items()
        if not items:
            return "NEWS: keine Feeds/keine Daten."
        headline_text = " | ".join(
            _format_news_item(item, include_summary=bool(item.summary)) for item in items
        )
        if command.topic:
            headline_text = f"Topic: {command.topic}. {headline_text}"
        if self.ollama_client:
            prompt = _build_news_prompt(headline_text)
            try:
                response = self.ollama_client.summarize(prompt)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("Ollama summarization failed: %s", exc)
                response = ""
            if response:
                return response
        return headline_text


def _format_news_item(item: NewsItem, include_summary: bool) -> str:
    source = getattr(item, "source", "NEWS")
    title = getattr(item, "title", "")
    summary = getattr(item, "summary", "")
    if include_summary and summary:
        return f"[{source}] {title} - {summary}"
    return f"[{source}] {title}"


def _build_news_prompt(headline_text: str) -> str:
    return (
        "Fasse die folgenden News extrem kurz zusammen.\n"
        "Regeln:\n"
        "- Deutsch.\n"
        "- Maximal 1-2 SMS (je ~140 Zeichen), insgesamt so kurz wie möglich.\n"
        "- Nur die wichtigsten Punkte, keine Einleitung, keine Floskeln.\n"
        "- Ausgabe als reiner Text.\n\n"
        f"News:\n{headline_text}"
    )
