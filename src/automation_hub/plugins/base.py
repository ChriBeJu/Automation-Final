from __future__ import annotations

from typing import Protocol

from automation_hub.models import Event


class Trigger(Protocol):
    name: str

    def poll(self) -> list[Event]:
        ...


class Action(Protocol):
    name: str

    def execute(self, event: Event) -> list[Event]:
        ...


class Processor(Protocol):
    name: str

    def process(self, event: Event) -> Event | None:
        ...
