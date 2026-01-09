from __future__ import annotations

from automation_hub.config import Config
from automation_hub.logging_utils import get_logger
from automation_hub.models import Event
from automation_hub.stores.state_store import StateStore


def normalize(event: Event) -> Event:
    return event


def dedupe(state_store: StateStore, event: Event) -> Event | None:
    if not event.dedupe_key:
        return event
    key = f"dedupe:{event.dedupe_key}"
    if state_store.has_processed(key):
        return None
    state_store.mark_processed(key)
    return event


def policy(config: Config, event: Event) -> Event | None:
    if event.event_type != "sms_inbound":
        return event
    sender = str(event.payload.get("sender"))
    if not config.allowed_sms_senders:
        return event
    if sender in config.allowed_sms_senders:
        return event
    logger = get_logger("automation_hub.policy", event.correlation_id)
    logger.info("Rejected SMS from unapproved sender %s", sender)
    return None


def llm_gate(config: Config, event: Event) -> Event | None:
    if not config.enable_llm:
        return event
    logger = get_logger("automation_hub.llm", event.correlation_id)
    logger.info("LLM step is enabled but not configured; skipping.")
    return event
