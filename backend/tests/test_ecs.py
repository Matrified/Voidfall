"""Entity Component System behaviour."""

import pytest

from voidfall.domain.components import Health, Name, Position
from voidfall.domain.world import ComponentExistsError, World


def test_spawn_gives_unique_ids():
    world = World()
    a, b, c = world.spawn(), world.spawn(), world.spawn()
    assert len({a, b, c}) == 3


def test_add_and_get_component():
    world = World()
    e = world.spawn()
    world.add(e, Name("torch"))
    assert world.get(e, Name).value == "torch"


def test_duplicate_component_rejected():
    world = World()
    e = world.spawn()
    world.add(e, Health(10, 10))
    with pytest.raises(ComponentExistsError):
        world.add(e, Health(5, 5))


def test_query_requires_all_components():
    world = World()
    a = world.spawn()
    world.add(a, Name("a"))
    world.add(a, Position(1))
    b = world.spawn()
    world.add(b, Name("b"))

    assert world.query(Name, Position) == [a]
    assert world.query(Name) == sorted([a, b])


def test_query_absent_component_is_empty():
    world = World()
    e = world.spawn()
    world.add(e, Name("lonely"))
    assert world.query(Name, Position) == []


def test_missing_component_returns_none():
    world = World()
    e = world.spawn()
    assert world.try_get(e, Name) is None


def test_remove_excludes_from_query():
    world = World()
    e = world.spawn()
    world.add(e, Name("x"))
    world.add(e, Position(1))
    world.remove(e, Position)
    assert world.query(Position) == []
    assert world.has(e, Name)
