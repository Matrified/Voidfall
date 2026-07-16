"""Property-based tests for the two guarantees the engine must never break:

1. Round-trip: deserialize(serialize(world)) reproduces the world exactly.
2. Determinism: the same action on equal worlds with the same seed/cursor is identical.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from voidfall.content import build_world
from voidfall.domain.actions import Action, ActionKind
from voidfall.domain.engine import Engine
from voidfall.domain.serialization import deserialize, serialize

# A vocabulary of commands to drive the world into varied states.
_COMMANDS = [
    "look", "north", "take torch", "inventory", "south", "north",
    "down", "attack ghoul", "up", "wait", "take sword", "equip sword",
]


def _play(seed: int, script: list[str]):
    from voidfall.parser import Parser

    world = build_world(seed=seed)
    engine, parser = Engine(), Parser()
    for text in script:
        result = parser.parse(text, world)
        if result.ok:
            engine.apply(world, result.action)
    return world


@settings(max_examples=60, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=2**31),
    script=st.lists(st.sampled_from(_COMMANDS), max_size=15),
)
def test_serialization_round_trip(seed, script):
    world = _play(seed, script)
    restored = deserialize(serialize(world))

    assert restored.entities == world.entities
    assert restored.turn == world.turn
    assert restored.player_id == world.player_id
    assert restored.rng.seed == world.rng.seed
    assert restored.rng.cursor == world.rng.cursor
    # Component stores compare equal by value.
    assert serialize(restored) == serialize(world)


@settings(max_examples=60, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=2**31),
    script=st.lists(st.sampled_from(_COMMANDS), max_size=12),
)
def test_determinism(seed, script):
    world_a = _play(seed, script)
    world_b = _play(seed, script)

    # Apply one more identical action to both and compare serialized state.
    engine = Engine()
    engine.apply(world_a, Action(ActionKind.WAIT))
    engine.apply(world_b, Action(ActionKind.WAIT))
    assert serialize(world_a) == serialize(world_b)
