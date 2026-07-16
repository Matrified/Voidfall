"""Save/load serialization for the world.

The world is serialized to a plain dict (JSON-friendly). Components are tagged by their
stable registry name rather than a Python path, so refactoring internal modules never
breaks existing saves. A schema version is recorded and checked on load; a migration
hook is provided for future format changes.

The guarantee: ``deserialize(serialize(world)) == world`` for every valid world. The
round-trip property test enforces this.
"""

from __future__ import annotations

from dataclasses import asdict, fields
from typing import Any, cast

from .components import COMPONENT_REGISTRY, COMPONENT_TAGS
from .quests import Objective, Quest
from .rng import Rng
from .world import World

SCHEMA_VERSION = 2


class SaveError(Exception):
    """Raised when a save payload cannot be loaded."""


def serialize(world: World) -> dict[str, Any]:
    """Serialize a world into a versioned, JSON-friendly dict."""
    components: dict[str, dict[str, Any]] = {}
    for component_type, store in world.components.items():
        tag = COMPONENT_TAGS.get(component_type)
        if tag is None:
            continue
        components[tag] = {
            str(eid): asdict(cast(Any, comp)) for eid, comp in store.items()
        }

    quests = [
        {
            "id": q.id,
            "name": q.name,
            "active": q.active,
            "completed": q.completed,
            "objectives": [
                {"text": o.text, "done": o.done, "flag": o.flag} for o in q.objectives
            ],
        }
        for q in world.quests
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "entities": sorted(world.entities),
        "next_id": world._next_id,
        "turn": world.turn,
        "player_id": world.player_id,
        "seed": world.seed,
        "rng": {"seed": world.rng.seed, "cursor": world.rng.cursor},
        "flags": dict(world.flags),
        "journal": list(world.journal),
        "quests": quests,
        "clock": world.clock,
        "weather": world.weather,
        "components": components,
    }


def _migrate(payload: dict[str, Any]) -> dict[str, Any]:
    """Upgrade an older payload to the current schema version.

    No historical migrations exist yet; this is the hook where they will live.
    """
    version = payload.get("schema_version")
    if version == SCHEMA_VERSION:
        return payload
    # v1 -> v2: narrative state (flags/journal/quests/clock/weather) was introduced.
    if version == 1:
        payload.setdefault("flags", {})
        payload.setdefault("journal", [])
        payload.setdefault("quests", [])
        payload.setdefault("clock", 300)
        payload.setdefault("weather", "Clear")
        payload["schema_version"] = 2
        return payload
    raise SaveError(f"unsupported save schema version: {version!r}")


def _build_component(tag: str, data: dict[str, Any]) -> object:
    component_cls = COMPONENT_REGISTRY[tag]
    field_names = {f.name for f in fields(component_cls)}
    kwargs = {k: v for k, v in data.items() if k in field_names}
    # Restore tuple-typed fields that JSON degrades to lists.
    for f in fields(component_cls):
        if f.name in kwargs and isinstance(kwargs[f.name], list) and "tuple" in str(f.type):
            kwargs[f.name] = tuple(kwargs[f.name])
    return component_cls(**kwargs)


def deserialize(payload: dict[str, Any]) -> World:
    """Reconstruct a world equal to the one that was serialized."""
    payload = _migrate(dict(payload))

    world = World()
    world.entities = set(payload["entities"])
    world._next_id = payload["next_id"]
    world.turn = payload["turn"]
    world.player_id = payload["player_id"]
    world.seed = payload["seed"]
    world.rng = Rng(seed=payload["rng"]["seed"], cursor=payload["rng"]["cursor"])
    world.flags = dict(payload["flags"])
    world.journal = list(payload["journal"])
    world.clock = payload["clock"]
    world.weather = payload["weather"]
    world.quests = [
        Quest(
            id=q["id"],
            name=q["name"],
            active=q["active"],
            completed=q["completed"],
            objectives=[
                Objective(text=o["text"], done=o["done"], flag=o["flag"])
                for o in q["objectives"]
            ],
        )
        for q in payload["quests"]
    ]

    for tag, store in payload["components"].items():
        if tag not in COMPONENT_REGISTRY:
            raise SaveError(f"unknown component tag: {tag!r}")
        component_type = COMPONENT_REGISTRY[tag]
        world.components[component_type] = {
            int(eid): _build_component(tag, data) for eid, data in store.items()
        }
    return world
