"""Character progression: experience, leveling, and attribute point allocation.

This is what makes the six attributes feel earned rather than decorative: defeating
foes and completing quests grants experience; leveling up grants an attribute point the
player spends deliberately (``allocate``). The engine — not the AI — is the sole
authority over when and how much experience is granted.
"""

from __future__ import annotations

from dataclasses import dataclass

from .components import Attributes, Progression

# Experience required for the next level grows each level, so progress is meaningful
# early and slows naturally rather than needing an arbitrary level cap.
_EXP_GROWTH = 1.35

EXP_KILL = 120
EXP_QUEST = 250

ATTRIBUTE_FIELDS = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")


@dataclass(frozen=True, slots=True)
class LevelUpResult:
    new_level: int
    attribute_points_gained: int


def grant_experience(progression: Progression, amount: int) -> list[LevelUpResult]:
    """Add experience and apply any number of resulting level-ups in order.

    Returns one :class:`LevelUpResult` per level gained (usually zero or one, but a large
    grant could cross multiple thresholds).
    """
    if amount <= 0:
        return []
    progression.exp += amount
    results: list[LevelUpResult] = []
    while progression.exp >= progression.exp_next:
        progression.exp -= progression.exp_next
        progression.level += 1
        progression.exp_next = int(progression.exp_next * _EXP_GROWTH)
        progression.attribute_points += 1
        results.append(LevelUpResult(progression.level, 1))
    return results


def allocate_attribute(attrs: Attributes, progression: Progression, field: str) -> bool:
    """Spend one pending attribute point on ``field``. Returns ``False`` if none pending
    or ``field`` is not a valid attribute name."""
    if progression.attribute_points <= 0 or field not in ATTRIBUTE_FIELDS:
        return False
    current = getattr(attrs, field)
    setattr(attrs, field, current + 1)
    progression.attribute_points -= 1
    return True
