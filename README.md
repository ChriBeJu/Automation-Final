# Automation Hub (Windows 10)

A modular, local automation hub that runs as a long-lived Windows 10 service and uses an attached Android device (via ADB) as the notification/SMS gateway.

## Architecture (Phase 0)

**Core concepts**
- **Events** are the canonical unit. Triggers emit standardized Events.
- **Pipeline** processes each Event through a consistent set of steps.
- **Actions** produce side effects and emit ActionResult Events.
- **Stores** persist everything (Event Store + State Store).

**Module layout**
```
src/automation_hub/
  adb/                # ADB integration + parsing
  actions/            # Side effects (SMS sending, command replies)
  pipeline/           # Pipeline and steps
  plugins/            # Plugin contracts + registry
  processors/         # Command parsing + routing
  stores/             # Event/State stores
  triggers/           # Event sources (WhatsApp notifications, SMS inbox)
  utils/              # Helpers (hashing, SMS splitting)
```

**Pipeline steps (testable, composable)**
1. Normalize
2. Deduplicate (State Store)
3. Policy (allow-list, safety checks)
4. Optional LLM gate (stub)
5. Route to actions
6. Store results

## MVP Features (Phase 1)

**Project A — WhatsApp Notification → SMS Forwarder**
- Polls Android notifications via `adb shell dumpsys notification --noredact`.
- Filters WhatsApp notifications.
- Formats messages as:
  ```
  [WA] <chat/sender> <timestamp>
  <content>
  ```
- Deduplicates messages and forwards exactly once.

**Project B — SMS Inbox Listener**
- Polls inbound SMS via `content://sms/inbox`.
- Parses lightweight commands (HELP, NEWS, INFO, N, !).
- Replies to HELP with supported commands.
- Sends stub replies for NEWS/INFO/N/!.

## Windows Setup

### 1) Prerequisites
- Python 3.11+
- Android Platform Tools (ADB)
- USB Debugging enabled on the phone

### 2) Device Setup
- Enable **USB debugging** in Developer Options.
- On first connection, accept the RSA prompt on the phone.
- Ensure SMS permissions are granted for `adb shell content` queries (some OEM ROMs may restrict access).

### 3) Run Setup Script
```powershell
powershell -ExecutionPolicy Bypass -File setup_windows.ps1
```

### 4) Configure
Edit `config.local.env` with:
- `SMS_FORWARD_NUMBER` (the number to receive forwarded WhatsApp messages)
- `ALLOWED_SMS_SENDERS` (allowed command senders)
- `ADB_DEVICE_ID` if multiple devices are attached

### 5) Run
```powershell
python -m automation_hub doctor
python -m automation_hub run
```

## CLI Commands
- `python -m automation_hub run` — start the long-running service
- `python -m automation_hub doctor` — check adb/device/config
- `python -m automation_hub tail` — tail recent events

## Configuration
Configuration is loaded from `config.local.env` (copy of `config.example.env`).

Key settings include:
- `ADB_PATH`, `ADB_DEVICE_ID`
- `SMS_FORWARD_NUMBER`
- `ALLOWED_SMS_SENDERS`
- `POLL_INTERVAL_SEC`
- Feature toggles: `ENABLE_SMS_COMMANDS`, `ENABLE_WHATSAPP_FORWARDING`, `ENABLE_LLM`

## Data & Logs
- Events are stored as JSONL in `data/events.jsonl`.
- State is stored in `data/state.db` (SQLite).
- Logs are written to `logs/automation_hub.log` (rotating).

## Troubleshooting

**adb unauthorized**
- Reconnect the device and accept the RSA prompt.
- Run `adb kill-server` and `adb start-server`.

**device offline**
- Unplug/replug USB.
- Check cable and USB mode.

**no notifications captured**
- WhatsApp notification parsing depends on `dumpsys notification --noredact` output.
- If your ROM restricts this, you may need to enable notification access for ADB or install a local notification listener app and adapt the trigger.

**SMS content query fails**
- Some OEM builds restrict `content://sms` access. If so, you may need to grant permissions via `adb shell appops` or use a helper app.

## Plugin Contracts
Plugins should implement the contracts in `automation_hub.plugins.base` and register themselves via the registry in `automation_hub.plugins.registry`. Plugins should not import core internals directly; they should only depend on the interfaces and injected dependencies.

## Development Notes
- All ADB parsing is isolated to `automation_hub/adb/adb_client.py`.
- Dependency injection is used for configuration and stores, enabling unit tests without ADB.

