"""The engine event bus.

Systems communicate through events rather than calling one another directly. The bus
delivers a published event to every subscriber registered for its type, in registration
order, and isolates subscriber failures so one bad handler cannot halt delivery.

Events are also collected into an ordered log on each action so the interface layer can
render exactly what happened without inspecting world internals.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Event:
    """Base class for all domain events."""


@dataclass(frozen=True, slots=True)
class EntityMoved(Event):
    entity_id: int
    from_room: int
    to_room: int


@dataclass(frozen=True, slots=True)
class RoomEntered(Event):
    entity_id: int
    room_id: int
    first_visit: bool


@dataclass(frozen=True, slots=True)
class InventoryChanged(Event):
    entity_id: int
    item_id: int
    added: bool


@dataclass(frozen=True, slots=True)
class EquipmentChanged(Event):
    entity_id: int
    item_id: int
    slot: str
    equipped: bool


@dataclass(frozen=True, slots=True)
class DamageDealt(Event):
    attacker_id: int
    defender_id: int
    amount: int


@dataclass(frozen=True, slots=True)
class CombatantDefeated(Event):
    entity_id: int


Subscriber = Callable[[Event], None]


@dataclass
class EventBus:
    """Publishes events to type-keyed subscribers and records an ordered log."""

    _subscribers: dict[type, list[Subscriber]] = field(default_factory=dict)
    log: list[Event] = field(default_factory=list)

    def subscribe(self, event_type: type, handler: Subscriber) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: Event) -> None:
        """Record the event, then deliver it to each subscriber in order.

        A subscriber that raises is skipped; delivery continues to the rest.
        """
        self.log.append(event)
        for handler in self._subscribers.get(type(event), []):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - isolation is the contract
                continue

    def drain(self) -> list[Event]:
        """Return and clear the accumulated event log."""
        events = self.log
        self.log = []
        return events
