from __future__ import annotations

from collections.abc import Iterable

from automation_hub.config import Config
from automation_hub.logging_utils import get_logger
from automation_hub.models import ActionResult, Event
from automation_hub.plugins.registry import PluginRegistry
from automation_hub.stores.event_store import EventStore
from automation_hub.stores.state_store import StateStore
from automation_hub.pipeline import steps


class Pipeline:
    def __init__(
        self,
        config: Config,
        state_store: StateStore,
        event_store: EventStore,
        registry: PluginRegistry,
    ) -> None:
        self.config = config
        self.state_store = state_store
        self.event_store = event_store
        self.registry = registry

    def process_event(self, event: Event) -> None:
        logger = get_logger("automation_hub.pipeline", event.correlation_id)
        normalized = steps.normalize(event)
        deduped = steps.dedupe(self.state_store, normalized)
        if deduped is None:
            logger.info("Event deduped",)
            return
        allowed = steps.policy(self.config, deduped)
        if allowed is None:
            return
        gated = steps.llm_gate(self.config, allowed)
        if gated is None:
            return
        results = self._route(gated)
        self.event_store.append(gated)
        self.event_store.append_all(results)

    def _route(self, event: Event) -> list[Event]:
        actions = self.registry.actions()
        results: list[Event] = []
        if event.event_type == "wa_notification" and self.config.enable_whatsapp_forwarding:
            action = actions.get("send_sms")
            if action:
                results.extend(action.execute(event))
        if event.event_type == "sms_inbound" and self.config.enable_sms_commands:
            action = actions.get("sms_command_router")
            if action:
                results.extend(action.execute(event))
        return results


def wrap_action_result(event: Event, result: ActionResult) -> Event:
    return Event(
        event_type="action_result",
        source=event.source,
        payload=result.to_event_payload(),
        correlation_id=event.correlation_id,
    )


def process_events(pipeline: Pipeline, events: Iterable[Event]) -> None:
    for event in events:
        pipeline.process_event(event)
