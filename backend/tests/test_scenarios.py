"""Every selectable scenario must build a valid, playable world."""

import pytest

from voidfall.content import build_scenario
from voidfall.domain.actions import Action, ActionKind
from voidfall.domain.components import Player, Position
from voidfall.domain.engine import Engine


@pytest.mark.parametrize("theme", ["medieval", "undead", "starship"])
def test_scenario_boots(theme):
    world, prologue = build_scenario(theme, seed=1)
    assert prologue
    # A player exists, is placed, and the opening LOOK resolves.
    assert world.player_id is not None
    assert world.has(world.player_id, Position)
    assert world.has(world.player_id, Player)
    outcome = Engine().apply(world, Action(ActionKind.LOOK))
    assert outcome.success
    assert world.quests  # each scenario ships at least one quest


def test_unknown_theme_falls_back_to_medieval():
    world, _ = build_scenario("nonsense", seed=1)
    assert world.player_id is not None
