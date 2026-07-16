"""Effective stat computation.

A creature's innate :class:`Stats` are its base. Equipped items add bonuses on top. Rather
than mutate the base when gear changes (which loses the innate values), we compute the
effective stats on demand by summing equipment bonuses. This keeps equip/unequip pure
moves and makes the math obvious and testable.
"""

from __future__ import annotations

from .components import Attributes, Equipment, Item, Stats
from .world import World


def effective_stats(world: World, entity_id: int) -> Stats:
    """Return combat stats: base + equipped-item bonuses + attribute modifiers.

    This is what makes Attributes mechanically real rather than decorative: Strength
    adds to attack, Dexterity adds to defense (reflexes), on top of gear.
    """
    base = world.try_get(entity_id, Stats) or Stats()
    attack, defense = base.attack, base.defense

    equipment = world.try_get(entity_id, Equipment)
    if equipment:
        for item_id in equipment.slots.values():
            item = world.try_get(item_id, Item)
            if item:
                attack += item.attack_bonus
                defense += item.defense_bonus

    attrs = world.try_get(entity_id, Attributes)
    if attrs:
        attack += attrs.modifier(attrs.strength)
        defense += attrs.modifier(attrs.dexterity)

    return Stats(attack=max(0, attack), defense=max(0, defense), speed=base.speed)


# Stamina economy: exertion actions cost stamina; a fatigued actor fights worse.
ATTACK_STAMINA_COST = 8
FORCE_BASE_STAMINA_COST = 18
FATIGUE_DAMAGE_PENALTY = 0.4  # damage multiplier when stamina is exhausted


def force_stamina_cost(world: World, entity_id: int) -> int:
    """Strength reduces the stamina cost of forcing something open."""
    attrs = world.try_get(entity_id, Attributes)
    modifier = attrs.modifier(attrs.strength) if attrs else 0
    return max(6, FORCE_BASE_STAMINA_COST - modifier * 3)


def rest_recovery(world: World, entity_id: int) -> tuple[int, int, int]:
    """Return (health, mana, stamina) recovered by resting, scaled by Constitution."""
    attrs = world.try_get(entity_id, Attributes)
    con_mod = attrs.modifier(attrs.constitution) if attrs else 0
    return (6 + max(0, con_mod) * 2, 8, 12 + max(0, con_mod) * 2)
