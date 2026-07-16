"""Combat system: deterministic, rule-based resolution.

Damage is a pure function of attacker stats, defender stats, and the RNG cursor. Given
equal worlds with the same seed and cursor, combat produces identical outcomes — which
the determinism property test verifies directly.
"""

from __future__ import annotations

from ..actions import Action, Outcome, OutcomeCode
from ..components import Actor, Health, Name, Position, Progression, Resources, Stats
from ..events import CombatantDefeated, DamageDealt, EventBus
from ..progression import EXP_KILL, grant_experience
from ..stats import ATTACK_STAMINA_COST, FATIGUE_DAMAGE_PENALTY, effective_stats
from ..world import World

_DAMAGE_MAX = 999_999


def _name_of(world: World, entity_id: int) -> str:
    name = world.try_get(entity_id, Name)
    return name.value if name else f"entity {entity_id}"


def _grant_kill_experience(world: World, player: int) -> list[str]:
    """Award experience for a kill and narrate any resulting level-ups."""
    progression = world.try_get(player, Progression)
    if progression is None:
        return []
    level_ups = grant_experience(progression, EXP_KILL)
    lines = [f"You gain {EXP_KILL} experience."]
    for result in level_ups:
        lines.append(
            f"You have reached level {result.new_level}! You feel a point of growth "
            f"settle into you — spend it with 'allocate <attribute>'."
        )
    return lines


def _compute_damage(attacker: Stats, defender: Stats, roll: int) -> int:
    """Base attack minus defense, plus a small deterministic swing."""
    base = attacker.attack + roll - defender.defense
    return max(0, min(base, _DAMAGE_MAX))


def apply_attack(world: World, action: Action, bus: EventBus) -> Outcome:
    """Resolve an ATTACK action, then let the target retaliate if it survives."""
    player = world.player_id
    assert player is not None
    target_id = action.target_id

    if target_id is None or not world.exists(target_id):
        return Outcome.fail(OutcomeCode.TARGET_NOT_FOUND, "There is nothing to attack.")

    target_actor = world.try_get(target_id, Actor)
    target_health = world.try_get(target_id, Health)
    if target_actor is None or target_health is None:
        return Outcome.fail(
            OutcomeCode.NOT_A_COMBATANT, f"The {_name_of(world, target_id)} cannot be fought."
        )

    # In range means "same room" in this slice.
    player_pos = world.get(player, Position)
    target_pos = world.try_get(target_id, Position)
    if target_pos is None or target_pos.room_id != player_pos.room_id:
        return Outcome.fail(OutcomeCode.OUT_OF_RANGE, "That target is not within reach.")

    player_stats = effective_stats(world, player)
    target_stats = effective_stats(world, target_id)

    lines: list[str] = []

    # Stamina gates combat effort: fighting winded deals reduced damage.
    resources = world.try_get(player, Resources)
    fatigued = bool(resources and resources.stamina < ATTACK_STAMINA_COST)
    if resources:
        resources.stamina = max(0, resources.stamina - ATTACK_STAMINA_COST)

    # Player strikes first.
    roll = world.rng.next_int(0, max(1, player_stats.attack))
    damage = _compute_damage(player_stats, target_stats, roll)
    if fatigued:
        damage = int(damage * FATIGUE_DAMAGE_PENALTY)
    target_health.current = max(0, target_health.current - damage)
    bus.publish(DamageDealt(player, target_id, damage))
    if fatigued:
        lines.append(
            f"Winded, you land a weak blow on the {_name_of(world, target_id)} "
            f"for {damage} damage."
        )
    else:
        lines.append(f"You strike the {_name_of(world, target_id)} for {damage} damage.")

    if target_health.current == 0:
        bus.publish(CombatantDefeated(target_id))
        lines.append(f"The {_name_of(world, target_id)} falls.")
        lines.extend(_grant_kill_experience(world, player))
        return Outcome.ok("\n".join(lines), tuple(bus.log))

    # Retaliation.
    roll = world.rng.next_int(0, max(1, target_stats.attack))
    damage = _compute_damage(target_stats, player_stats, roll)
    player_health = world.get(player, Health)
    player_health.current = max(0, player_health.current - damage)
    bus.publish(DamageDealt(target_id, player, damage))
    lines.append(f"The {_name_of(world, target_id)} hits back for {damage} damage.")

    if player_health.current == 0:
        bus.publish(CombatantDefeated(player))
        lines.append("Darkness takes you. You have fallen.")

    return Outcome.ok("\n".join(lines), tuple(bus.log))
