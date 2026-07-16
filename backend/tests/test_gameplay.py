"""End-to-end engine behaviour: movement, inventory, equipment, combat."""

import pytest

from voidfall.content import build_world
from voidfall.domain.actions import ActionKind, OutcomeCode
from voidfall.domain.components import Equipment, Health, Inventory, Position
from voidfall.domain.engine import Engine
from voidfall.parser import Parser


@pytest.fixture
def game():
    world = build_world()
    return world, Engine(), Parser()


def _run(game, text):
    world, engine, parser = game
    result = parser.parse(text, world)
    assert result.ok, f"parse failed: {result.message}"
    return engine.apply(world, result.action)


def test_move_updates_position(game):
    world, _, _ = game
    _run(game, "go north")
    assert world.get(world.player_id, Position).room_id != 1


def test_blocked_direction(game):
    # The gate opens north and west; "up" leads nowhere.
    outcome = _run(game, "go up")
    assert not outcome.success
    assert outcome.code is OutcomeCode.BLOCKED_MOVEMENT


def test_locked_passage(game):
    _run(game, "north")  # into the hall
    outcome = _run(game, "east")  # sealed door
    assert not outcome.success
    assert outcome.code is OutcomeCode.PASSAGE_BLOCKED


def test_take_and_inventory(game):
    world, _, _ = game
    before = len(world.get(world.player_id, Inventory).items)
    outcome = _run(game, "take torch")
    assert outcome.success
    assert len(world.get(world.player_id, Inventory).items) == before + 1


def test_equip_boosts_attack(game):
    from voidfall.domain.stats import effective_stats

    world, _, _ = game
    _run(game, "north")
    _run(game, "take sword")
    before = effective_stats(world, world.player_id).attack
    outcome = _run(game, "equip sword")
    assert outcome.success
    after = effective_stats(world, world.player_id).attack
    assert after > before
    assert world.get(world.player_id, Equipment).slots.get("hand") is not None


def test_combat_reduces_health_and_can_defeat(game):
    world, engine, parser = game
    # Travel to the crypt where the ghoul waits.
    _run(game, "north")
    _run(game, "take sword")
    _run(game, "equip sword")
    _run(game, "down")

    from voidfall.domain.components import Actor

    ghoul = world.query(Actor)[0]
    ghoul_start = world.get(ghoul, Health).current
    result = parser.parse("attack ghoul", world)
    outcome = engine.apply(world, result.action)
    assert outcome.success
    assert world.get(ghoul, Health).current < ghoul_start


def test_semantic_movement(game):
    # "go inside" (no compass direction) should still move the player.
    world, engine, parser = game
    start = world.get(world.player_id, Position).room_id
    result = parser.parse("go inside", world)
    assert result.ok and result.action.kind is ActionKind.MOVE
    engine.apply(world, result.action)
    assert world.get(world.player_id, Position).room_id != start


def test_movement_by_room_name_beats_literal_in(game):
    # "walk in" alone is ambiguous; naming the actual destination must resolve to it,
    # not silently fail like the bare word "in" would from a room with no "in" exit.
    world, engine, parser = game
    result = parser.parse("walk in the hall of echoes", world)
    assert result.ok and result.action.kind is ActionKind.MOVE
    outcome = engine.apply(world, result.action)
    assert outcome.success


def test_unlock_with_key_opens_the_way(game):
    from voidfall.domain.components import Hidden, Inventory, Name

    world, engine, parser = game
    # Give the player the iron key directly (normally found under the cart).
    key = next(
        e for e in world.query(Name)
        if "iron key" in world.get(e, Name).value
    )
    world.remove(key, Hidden)
    world.remove(key, Position)
    world.get(world.player_id, Inventory).items.append(key)

    _run(game, "north")  # into the hall, where the east door is locked
    blocked = _run(game, "go east")
    assert not blocked.success and blocked.code is OutcomeCode.PASSAGE_BLOCKED

    unlocked = _run(game, "unlock the east door")
    assert unlocked.success

    opened = _run(game, "go east")
    assert opened.success  # the vault is now reachable


def test_unlock_without_key_fails(game):
    _run(game, "north")
    outcome = _run(game, "open the door")
    assert not outcome.success
    assert outcome.code is OutcomeCode.NO_KEY


def test_force_verb_opens_locked_way_with_a_tool(game):
    # "force"/"pry" are equivalent to unlock when the player carries a tool marked
    # is_key (e.g. a crowbar) — this is the exact phrasing that previously fell through
    # to free-form narration and lied about success.
    from voidfall.domain.components import Hidden, Inventory, Name

    world, engine, parser = game
    key = next(e for e in world.query(Name) if "iron key" in world.get(e, Name).value)
    world.remove(key, Hidden)
    world.remove(key, Position)
    world.get(world.player_id, Inventory).items.append(key)

    _run(game, "north")
    result = parser.parse("pry the door open using the key", world)
    assert result.ok and result.action.kind is ActionKind.UNLOCK
    outcome = engine.apply(world, result.action)
    assert outcome.success

    entered = _run(game, "go east")
    assert entered.success


def test_forcing_costs_stamina(game):
    from voidfall.domain.components import Hidden, Inventory, Name, Resources

    world, engine, parser = game
    key = next(e for e in world.query(Name) if "iron key" in world.get(e, Name).value)
    world.remove(key, Hidden)
    world.remove(key, Position)
    world.get(world.player_id, Inventory).items.append(key)

    _run(game, "north")
    before = world.get(world.player_id, Resources).stamina
    result = parser.parse("force the door", world)
    engine.apply(world, result.action)
    after = world.get(world.player_id, Resources).stamina
    assert after < before


def test_attacking_costs_stamina(game):
    from voidfall.domain.components import Resources

    world, engine, parser = game
    _run(game, "north")
    _run(game, "down")
    before = world.get(world.player_id, Resources).stamina
    result = parser.parse("attack ghoul", world)
    engine.apply(world, result.action)
    after = world.get(world.player_id, Resources).stamina
    assert after < before


def test_rest_scales_with_constitution(game):
    from voidfall.domain.actions import Action, ActionKind
    from voidfall.domain.components import Attributes, Health, Resources

    world, engine, _ = game
    world.get(world.player_id, Health).current = 100
    world.get(world.player_id, Resources).stamina = 0
    world.set(world.player_id, Attributes(constitution=20))  # high CON

    engine.apply(world, Action(ActionKind.WAIT))
    high_con_gain = world.get(world.player_id, Resources).stamina

    world.get(world.player_id, Resources).stamina = 0
    world.set(world.player_id, Attributes(constitution=8))  # low CON
    engine.apply(world, Action(ActionKind.WAIT))
    low_con_gain = world.get(world.player_id, Resources).stamina

    assert high_con_gain > low_con_gain


def test_killing_grants_experience_and_can_level_up(game):
    from voidfall.domain.components import Progression

    world, engine, parser = game
    prog = world.get(world.player_id, Progression)
    prog.exp_next = 50  # force a level-up on the first kill for a deterministic test
    before_level = prog.level

    _run(game, "north")
    _run(game, "down")
    # Attack until the ghoul falls (bounded loop to avoid an infinite test on bad luck).
    for _ in range(30):
        outcome = _run(game, "attack ghoul")
        if "falls" in outcome.message:
            break
    assert world.get(world.player_id, Progression).level > before_level
    assert world.get(world.player_id, Progression).attribute_points >= 1


def test_allocate_spends_a_level_up_point(game):
    from voidfall.domain.components import Attributes, Progression

    world, engine, parser = game
    world.get(world.player_id, Progression).attribute_points = 1
    before = world.get(world.player_id, Attributes).strength

    outcome = _run(game, "allocate strength")
    assert outcome.success
    assert world.get(world.player_id, Attributes).strength == before + 1
    assert world.get(world.player_id, Progression).attribute_points == 0


def test_allocate_without_points_fails(game):
    outcome = _run(game, "allocate strength")
    assert not outcome.success
    assert outcome.code is OutcomeCode.NO_POINTS


def test_attack_out_of_range(game):
    # The ghoul is in the crypt; the player starts at the gate.
    world, engine, parser = game
    # Manually target the ghoul id while out of range.
    from voidfall.domain.actions import Action
    from voidfall.domain.components import Actor

    ghoul = world.query(Actor)[0]
    outcome = engine.apply(world, Action(ActionKind.ATTACK, target_id=ghoul))
    assert not outcome.success
    assert outcome.code is OutcomeCode.OUT_OF_RANGE
