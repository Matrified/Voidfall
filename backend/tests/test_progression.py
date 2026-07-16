"""Experience, leveling, and attribute allocation."""

from voidfall.domain.components import Attributes, Progression
from voidfall.domain.progression import allocate_attribute, grant_experience


def test_experience_accumulates_without_leveling():
    prog = Progression(level=1, exp=0, exp_next=300)
    results = grant_experience(prog, 100)
    assert results == []
    assert prog.exp == 100
    assert prog.level == 1


def test_level_up_grants_an_attribute_point():
    prog = Progression(level=1, exp=280, exp_next=300)
    results = grant_experience(prog, 50)
    assert len(results) == 1
    assert results[0].new_level == 2
    assert prog.attribute_points == 1
    assert prog.exp == 30  # 280 + 50 - 300


def test_large_grant_can_cross_multiple_levels():
    prog = Progression(level=1, exp=0, exp_next=100)
    results = grant_experience(prog, 1000)
    assert len(results) >= 2
    assert prog.attribute_points == len(results)


def test_zero_or_negative_grant_is_a_no_op():
    prog = Progression(level=1, exp=50, exp_next=300)
    assert grant_experience(prog, 0) == []
    assert grant_experience(prog, -10) == []
    assert prog.exp == 50


def test_allocate_spends_a_point_and_increases_attribute():
    attrs = Attributes(strength=10)
    prog = Progression(attribute_points=1)
    assert allocate_attribute(attrs, prog, "strength") is True
    assert attrs.strength == 11
    assert prog.attribute_points == 0


def test_allocate_fails_with_no_points():
    attrs = Attributes(strength=10)
    prog = Progression(attribute_points=0)
    assert allocate_attribute(attrs, prog, "strength") is False
    assert attrs.strength == 10


def test_allocate_rejects_unknown_field():
    attrs = Attributes()
    prog = Progression(attribute_points=1)
    assert allocate_attribute(attrs, prog, "luck") is False
    assert prog.attribute_points == 1
