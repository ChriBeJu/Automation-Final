from __future__ import annotations

from typing import Iterable

from automation_hub.plugins.base import Action, Processor, Trigger


class PluginRegistry:
    def __init__(self) -> None:
        self._triggers: dict[str, Trigger] = {}
        self._actions: dict[str, Action] = {}
        self._processors: dict[str, Processor] = {}

    def register_trigger(self, trigger: Trigger) -> None:
        self._triggers[trigger.name] = trigger

    def register_action(self, action: Action) -> None:
        self._actions[action.name] = action

    def register_processor(self, processor: Processor) -> None:
        self._processors[processor.name] = processor

    def triggers(self) -> Iterable[Trigger]:
        return self._triggers.values()

    def actions(self) -> dict[str, Action]:
        return dict(self._actions)

    def processors(self) -> Iterable[Processor]:
        return self._processors.values()
