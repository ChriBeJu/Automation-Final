from __future__ import annotations

import argparse
import time
from pathlib import Path

from automation_hub.adb.adb_client import AdbClient
from automation_hub.actions.sms_sender import SmsSenderAction
from automation_hub.config import ensure_directories, load_config
from automation_hub.logging_utils import configure_logging, get_logger
from automation_hub.pipeline.pipeline import Pipeline, process_events
from automation_hub.plugins.registry import PluginRegistry
from automation_hub.processors.command_router import SmsCommandRouterAction
from automation_hub.stores.event_store import EventStore
from automation_hub.stores.state_store import StateStore
from automation_hub.triggers.sms_inbox import SmsInboxTrigger
from automation_hub.triggers.whatsapp_notifications import WhatsAppNotificationTrigger


def main() -> int:
    parser = argparse.ArgumentParser(prog="automation_hub")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run")
    subparsers.add_parser("doctor")
    tail_parser = subparsers.add_parser("tail")
    tail_parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if args.command == "doctor":
        return run_doctor()
    if args.command == "tail":
        return run_tail(args.limit)
    return run_service()


def run_service() -> int:
    config = load_config()
    ensure_directories([config.event_store_path.parent, config.state_store_path.parent, config.log_dir])
    configure_logging(config.log_dir)
    logger = get_logger("automation_hub")
    adb_client = AdbClient(config.adb_path, config.device_id)
    event_store = EventStore(config.event_store_path)
    state_store = StateStore(config.state_store_path)
    registry = PluginRegistry()

    if config.enable_whatsapp_polling:
        registry.register_trigger(WhatsAppNotificationTrigger(adb_client))
    registry.register_trigger(SmsInboxTrigger(adb_client))
    registry.register_action(SmsSenderAction(adb_client, config))
    registry.register_action(SmsCommandRouterAction(adb_client, config))

    pipeline = Pipeline(config, state_store, event_store, registry)

    logger.info("Automation hub started")
    try:
        while True:
            for trigger in registry.triggers():
                try:
                    events = trigger.poll()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Trigger %s failed: %s", trigger.name, exc)
                    continue
                process_events(pipeline, events)
            time.sleep(config.poll_interval_sec)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        state_store.close()
    return 0


def run_doctor() -> int:
    config = load_config()
    configure_logging(config.log_dir)
    logger = get_logger("automation_hub.doctor")
    adb_client = AdbClient(config.adb_path, config.device_id)
    try:
        devices = adb_client.list_devices()
    except Exception as exc:  # noqa: BLE001
        logger.error("ADB error: %s", exc)
        return 1
    if not devices:
        logger.error("No devices detected")
        return 1
    logger.info("Devices detected: %s", ", ".join(devices))
    if config.device_id and config.device_id not in devices:
        logger.error("Configured device_id not in devices list")
        return 1
    logger.info("Doctor checks passed")
    return 0


def run_tail(limit: int) -> int:
    config = load_config()
    event_store = EventStore(config.event_store_path)
    for item in event_store.tail(limit):
        print(item)
    log_path = config.log_dir / "automation_hub.log"
    if log_path.exists():
        print(f"\nLog file: {log_path}")
    return 0
