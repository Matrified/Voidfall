"""Save/load specifics: schema versioning and migration rejection."""

import pytest

from voidfall.content import build_world
from voidfall.domain.serialization import (
    SCHEMA_VERSION,
    SaveError,
    deserialize,
    serialize,
)


def test_save_records_schema_version():
    payload = serialize(build_world())
    assert payload["schema_version"] == SCHEMA_VERSION


def test_unknown_version_rejected():
    payload = serialize(build_world())
    payload["schema_version"] = 999
    with pytest.raises(SaveError):
        deserialize(payload)


def test_unknown_component_tag_rejected():
    payload = serialize(build_world())
    payload["components"]["Nonsense"] = {"1": {}}
    with pytest.raises(SaveError):
        deserialize(payload)


def test_round_trip_preserves_rng_position():
    world = build_world(seed=555)
    world.rng.next_int(0, 10)  # advance the cursor
    restored = deserialize(serialize(world))
    assert restored.rng.cursor == world.rng.cursor
    assert restored.rng.seed == world.rng.seed
