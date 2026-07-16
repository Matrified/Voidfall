"""Free-form interpretation and the authoritative effects boundary."""

from voidfall.content import build_world
from voidfall.domain.components import Health, Hidden, Position
from voidfall.domain.effects import Effect, apply_effects
from voidfall.narration.interpreter import Interpreter


def _hidden_in_room(world, room_id):
    return [
        e for e in world.query(Hidden, Position)
        if world.get(e, Position).room_id == room_id
    ]


def test_engine_fallback_reveals_hidden_by_keyword():
    # With no LLM provider, "search the cart" should still surface the authored key.
    world = build_world()
    interpreter = Interpreter(provider=None)
    gate = world.get(world.player_id, Position).room_id
    assert _hidden_in_room(world, gate)  # the iron key is hidden under the cart

    before = len(_hidden_in_room(world, gate))
    result = interpreter.interpret(world, "search the broken cart in the mud")
    apply_effects(world, result.effects)

    assert len(_hidden_in_room(world, gate)) == before - 1  # the key was revealed
    assert any("iron key" in entry.lower() for entry in world.journal)


def test_reveal_requires_matching_keyword():
    world = build_world()
    interpreter = Interpreter(provider=None)
    gate = world.get(world.player_id, Position).room_id
    before = len(_hidden_in_room(world, gate))

    result = interpreter.interpret(world, "admire the sky")
    apply_effects(world, result.effects)

    assert len(_hidden_in_room(world, gate)) == before  # nothing revealed


def test_discovery_advances_quests():
    # Revealing the caravan's silver in the crypt sets the flag that completes a quest.
    from voidfall.domain.actions import Action, ActionKind
    from voidfall.domain.engine import Engine

    world = build_world()
    interpreter = Interpreter(provider=None)
    # Walk to the crypt: gate -> hall -> crypt.
    engine = Engine()
    engine.apply(world, Action(ActionKind.MOVE, direction="north"))
    engine.apply(world, Action(ActionKind.MOVE, direction="down"))

    result = interpreter.interpret(world, "pry at the loose flagstone on the floor")
    apply_effects(world, result.effects)
    engine.tick(world)

    assert world.flags.get("found_caravan") is True
    caravan_quest = next(q for q in world.quests if q.id == "missing_caravan")
    assert caravan_quest.completed


def test_high_wisdom_catches_near_miss_phrasing():
    from voidfall.domain.components import Attributes
    from voidfall.domain.effects import reveal_by_text

    world = build_world()
    gate = world.get(world.player_id, Position).room_id
    # "wheeze" shares a 4-char prefix ("whee") with the authored keyword "wheel" but is
    # not a substring match of it — a genuine near-miss, not an exact hit.
    world.set(world.player_id, Attributes(wisdom=18))  # modifier +4, well over threshold
    before = len(_hidden_in_room(world, gate))

    notes = reveal_by_text(world, "you wheeze, peering at the debris in the yard")
    assert notes
    assert len(_hidden_in_room(world, gate)) < before


def test_low_wisdom_misses_near_miss_phrasing():
    from voidfall.domain.components import Attributes
    from voidfall.domain.effects import reveal_by_text

    world = build_world()
    gate = world.get(world.player_id, Position).room_id
    world.set(world.player_id, Attributes(wisdom=6))  # modifier -2, below threshold
    before = len(_hidden_in_room(world, gate))

    notes = reveal_by_text(world, "you wheeze, peering at the debris in the yard")
    assert notes == []
    assert len(_hidden_in_room(world, gate)) == before


def test_reveal_by_text_is_deterministic():
    # Regardless of any LLM, keyword-matching surfaces authored hidden content + flags.
    from voidfall.domain.effects import reveal_by_text

    world = build_world()
    gate = world.get(world.player_id, Position).room_id
    before = len(_hidden_in_room(world, gate))

    notes = reveal_by_text(world, "dig through the mud beneath the cart")
    assert notes  # the key surfaced
    assert len(_hidden_in_room(world, gate)) < before


def test_effects_are_clamped():
    world = build_world()
    player = world.player_id
    world.get(player, Health).current = 100

    # An absurd heal is clamped to the sanctioned maximum.
    apply_effects(world, [Effect("heal", {"amount": 9999})])
    assert world.get(player, Health).current <= 108  # 100 + MAX_HEAL(8)


def test_unknown_effect_kind_is_dropped():
    world = build_world()
    # A made-up effect must not raise and must change nothing.
    lines = apply_effects(world, [Effect("grant_10000_gold", {"amount": 10000})])
    assert lines == []
