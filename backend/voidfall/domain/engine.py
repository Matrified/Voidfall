"""The Engine: the single authority that applies actions to the world.

The engine is the only component permitted to mutate world state. It dispatches each
action to the responsible system, collects the produced events into the outcome, and
returns an authoritative result. It has no knowledge of HTTP, databases, or the LLM.
"""

from __future__ import annotations

from .actions import Action, ActionKind, Outcome, OutcomeCode
from .components import Attributes, Position, Progression
from .events import EventBus
from .progression import EXP_QUEST, allocate_attribute, grant_experience
from .systems import combat, inventory, movement
from .systems.inventory import render_inventory
from .systems.movement import describe_room
from .world import World


class Engine:
    """Applies actions to a world and returns deterministic outcomes."""

    def tick(self, world: World) -> list[str]:
        """Advance world time and refresh quests after a turn.

        Returns any narration lines produced by newly completed quests. Deterministic:
        driven only by the turn counter and the RNG.
        """
        world.clock += 10
        # A gentle, deterministic weather drift every few turns.
        if world.turn % 6 == 0:
            world.weather = world.rng.next_int(0, 1) and "Rain" or "Clear"

        lines: list[str] = []
        for quest in world.quests:
            if quest.refresh(world.flags):
                lines.append(f"Quest complete: {quest.name}.")
                assert world.player_id is not None
                progression = world.try_get(world.player_id, Progression)
                if progression:
                    lines.append(f"You gain {EXP_QUEST} experience for your resolve.")
                    for result in grant_experience(progression, EXP_QUEST):
                        lines.append(
                            f"You have reached level {result.new_level}! Spend your "
                            f"growth with 'allocate <attribute>'."
                        )
        return lines

    def apply(self, world: World, action: Action) -> Outcome:
        """Resolve ``action`` against ``world`` and return the outcome.

        A fresh event bus is used per action so the outcome carries exactly the events
        that this action produced.
        """
        if world.player_id is None:
            return Outcome.fail(OutcomeCode.INVALID, "The world has no player.")

        bus = EventBus()
        world.turn += 1

        match action.kind:
            case ActionKind.LOOK:
                room_id = world.get(world.player_id, Position).room_id
                return Outcome.ok(describe_room(world, room_id))
            case ActionKind.INVENTORY:
                return Outcome.ok(render_inventory(world))
            case ActionKind.WAIT:
                return self._rest(world)
            case ActionKind.MOVE:
                return movement.apply_move(world, action, bus)
            case ActionKind.UNLOCK:
                return movement.apply_unlock(world, action, bus)
            case ActionKind.TAKE:
                return inventory.apply_take(world, action, bus)
            case ActionKind.DROP:
                return inventory.apply_drop(world, action, bus)
            case ActionKind.EQUIP:
                return inventory.apply_equip(world, action, bus)
            case ActionKind.UNEQUIP:
                return inventory.apply_unequip(world, action, bus)
            case ActionKind.ATTACK:
                return combat.apply_attack(world, action, bus)
            case ActionKind.ALLOCATE:
                return self._allocate(world, action)

        return Outcome.fail(OutcomeCode.INVALID, "The engine does not understand that.")

    def _allocate(self, world: World, action: Action) -> Outcome:
        """Spend a pending attribute point earned from leveling up."""
        player = world.player_id
        assert player is not None
        field = action.target_attribute
        progression = world.try_get(player, Progression)
        attrs = world.try_get(player, Attributes)

        if not field or attrs is None or progression is None:
            return Outcome.fail(
                OutcomeCode.INVALID,
                "Name an attribute to grow: strength, dexterity, constitution, "
                "intelligence, wisdom, or charisma.",
            )
        if progression.attribute_points <= 0:
            return Outcome.fail(
                OutcomeCode.NO_POINTS, "You have no unspent growth to allocate yet."
            )
        allocate_attribute(attrs, progression, field)
        return Outcome.ok(
            f"You feel your {field} sharpen. ({progression.attribute_points} point"
            f"{'s' if progression.attribute_points != 1 else ''} remaining.)"
        )

    def _rest(self, world: World) -> Outcome:
        """Resting restores health, mana, and stamina — Constitution improves recovery."""
        from .components import Health, Resources
        from .stats import rest_recovery

        player = world.player_id
        assert player is not None
        hp_gain, mp_gain, sta_gain = rest_recovery(world, player)
        hp = world.try_get(player, Health)
        res = world.try_get(player, Resources)
        if hp:
            hp.current = min(hp.maximum, hp.current + hp_gain)
        if res:
            res.mana = min(res.mana_max, res.mana + mp_gain)
            res.stamina = min(res.stamina_max, res.stamina + sta_gain)
        return Outcome.ok(
            "You steady your breath. The ache in your limbs eases, and the world "
            "turns quietly around you while you recover."
        )
