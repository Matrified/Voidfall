"""The parser resolves canonical actions and routes everything else to free-form."""

import pytest

from voidfall.content import build_world
from voidfall.domain.actions import ActionKind
from voidfall.parser import Parser


@pytest.fixture
def world():
    return build_world()


@pytest.fixture
def parser():
    return Parser()


def test_bare_direction_is_movement(parser, world):
    result = parser.parse("north", world)
    assert result.ok
    assert result.action.kind is ActionKind.MOVE
    assert result.action.direction == "north"


def test_verb_and_direction(parser, world):
    result = parser.parse("walk north", world)
    assert result.action.kind is ActionKind.MOVE
    assert result.action.direction == "north"


def test_modifiers_preserved_and_stripped(parser, world):
    result = parser.parse("carefully go north while keeping my sword raised", world)
    assert result.action.kind is ActionKind.MOVE
    assert result.action.direction == "north"
    assert "carefully" in result.action.modifiers
    assert any("sword raised" in m for m in result.action.modifiers)


def test_take_resolves_target_in_room(parser, world):
    result = parser.parse("take the torch", world)
    assert result.ok
    assert result.action.kind is ActionKind.TAKE
    assert result.action.target_id is not None


def test_bare_look_is_canonical(parser, world):
    result = parser.parse("look", world)
    assert result.ok and result.action.kind is ActionKind.LOOK


def test_look_at_something_is_freeform(parser, world):
    result = parser.parse("look in the crack", world)
    assert result.is_freeform
    assert result.freeform == "look in the crack"


def test_unknown_verb_is_freeform(parser, world):
    result = parser.parse("pray to the old gods", world)
    assert result.is_freeform


def test_take_missing_item_is_freeform(parser, world):
    # There is no crown here; rather than erroring, hand it to interpretation.
    result = parser.parse("take the golden crown", world)
    assert result.is_freeform


def test_empty_input_asks_for_clarification(parser, world):
    result = parser.parse("   ", world)
    assert not result.ok
    assert result.clarify is not None


def test_parser_needs_no_llm(parser, world):
    # Canonical resolution never touches an LLM; the parser has no such dependency.
    assert parser.parse("inventory", world).action.kind is ActionKind.INVENTORY
