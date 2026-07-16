"""The World: the authoritative Entity Component System store.

The world owns every entity, every component, the deterministic RNG, and a little
session metadata (turn counter, the player entity, generation seed). It exposes a small,
deliberate API for spawning entities and attaching/removing/querying components. Systems
operate exclusively through this API — they never reach into the internal dictionaries.

Equality is by value: two worlds are equal when their entities, components, and RNG
position match. This is the property the determinism and save/load tests rely on.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TypeVar

from .quests import Quest
from .rng import Rng

T = TypeVar("T")

# The passage of time. Each turn advances the clock; the world cycles through phases.
TIME_PHASES = ("Dawn", "Morning", "Noon", "Afternoon", "Dusk", "Night", "Deep Night")


class ComponentExistsError(Exception):
    """Raised when adding a component type an entity already has."""


@dataclass
class World:
    """Authoritative game state.

    Attributes:
        entities: Set of live entity ids.
        components: type -> {entity_id -> component instance}.
        rng: The deterministic random source.
        turn: Monotonic game-turn counter.
        player_id: The player entity, or ``None`` before the world is seeded.
        seed: The procedural-generation seed recorded for this world.
        flags: Named story flags set by events or sanctioned free-form effects.
        journal: An ordered log of discoveries and lore for the player.
        quests: The quest log.
        clock: Minutes elapsed in-world (drives the time-of-day phase).
        weather: Current weather descriptor.
    """

    entities: set[int] = field(default_factory=set)
    components: dict[type, dict[int, object]] = field(default_factory=dict)
    rng: Rng = field(default_factory=lambda: Rng(seed=0))
    turn: int = 0
    player_id: int | None = None
    seed: int = 0
    flags: dict[str, bool] = field(default_factory=dict)
    journal: list[str] = field(default_factory=list)
    quests: list[Quest] = field(default_factory=list)
    clock: int = 300  # start mid-morning
    weather: str = "Clear"
    _next_id: int = 1

    @property
    def time_phase(self) -> str:
        """Return the current time-of-day label derived from the clock."""
        index = (self.clock // 180) % len(TIME_PHASES)
        return TIME_PHASES[index]

    # -- entity lifecycle ---------------------------------------------------

    def spawn(self) -> int:
        """Create a new empty entity and return its unique id."""
        entity_id = self._next_id
        self._next_id += 1
        self.entities.add(entity_id)
        return entity_id

    def despawn(self, entity_id: int) -> None:
        """Remove an entity and all of its components."""
        self.entities.discard(entity_id)
        for store in self.components.values():
            store.pop(entity_id, None)

    def exists(self, entity_id: int) -> bool:
        return entity_id in self.entities

    # -- component operations ----------------------------------------------

    def add(self, entity_id: int, component: object) -> None:
        """Attach a component. Rejects a duplicate of the same type (R2.6)."""
        if entity_id not in self.entities:
            raise KeyError(f"unknown entity {entity_id}")
        store = self.components.setdefault(type(component), {})
        if entity_id in store:
            raise ComponentExistsError(
                f"entity {entity_id} already has {type(component).__name__}"
            )
        store[entity_id] = component

    def set(self, entity_id: int, component: object) -> None:
        """Attach or replace a component of its type."""
        self.components.setdefault(type(component), {})[entity_id] = component

    def remove(self, entity_id: int, component_type: type) -> None:
        store = self.components.get(component_type)
        if store is not None:
            store.pop(entity_id, None)

    def try_get(self, entity_id: int, component_type: type[T]) -> T | None:
        """Return the component, or ``None`` if the entity lacks it (R2.8)."""
        return self.components.get(component_type, {}).get(entity_id)  # type: ignore[return-value]

    def get(self, entity_id: int, component_type: type[T]) -> T:
        """Return the component or raise ``KeyError`` if absent."""
        component = self.try_get(entity_id, component_type)
        if component is None:
            raise KeyError(f"entity {entity_id} has no {component_type.__name__}")
        return component

    def has(self, entity_id: int, component_type: type) -> bool:
        return entity_id in self.components.get(component_type, {})

    def query(self, *component_types: type) -> list[int]:
        """Return every entity possessing *all* of the given component types (R2.3).

        Results are sorted by entity id so iteration order is deterministic.
        """
        if not component_types:
            return sorted(self.entities)
        stores = [self.components.get(ct, {}) for ct in component_types]
        if any(not store for store in stores):
            return []
        smallest = min(stores, key=len)
        return sorted(
            eid for eid in smallest if all(eid in store for store in stores)
        )

    def clone(self) -> World:
        """Return a deep, independent copy — used by determinism tests."""
        return copy.deepcopy(self)
