"""Game session orchestration.

The seam between the pure engine and the outside world. It holds active worlds in memory
(keyed by an opaque session id), runs the parse -> engine/interpret -> narrate pipeline,
applies any AI-proposed effects through the authoritative effect layer, and assembles the
rich view the terminal renders.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from ..content import build_scenario
from ..domain.actions import Action, ActionKind, Outcome, OutcomeCode
from ..domain.components import (
    Actor,
    Attributes,
    Equipment,
    Health,
    Hidden,
    Inventory,
    Item,
    Name,
    Player,
    Position,
    Progression,
    Resources,
    Room,
)
from ..domain.effects import apply_effects, reveal_by_text
from ..domain.engine import Engine
from ..domain.events import CombatantDefeated, DamageDealt
from ..domain.world import World
from ..narration import Interpreter, Narrator, build_provider
from ..parser import Parser
from .schemas import (
    AttributeView,
    EntityView,
    ExitView,
    GameView,
    ItemView,
    PlayerView,
    QuestObjectiveView,
    QuestView,
)

_ROOM_CHANGING = {ActionKind.MOVE, ActionKind.LOOK, ActionKind.UNLOCK}


@dataclass
class _Session:
    world: World
    owner_id: int | None


class GameService:
    """Owns active sessions and the full turn pipeline."""

    def __init__(self) -> None:
        self._engine = Engine()
        self._parser = Parser()
        self._narrator = Narrator()
        self._interpreter = Interpreter(build_provider())
        self._sessions: dict[str, _Session] = {}

    # -- lifecycle ---------------------------------------------------------

    def new_game(self, theme: str, seed: int, owner_id: int | None, player_name: str | None = None) -> GameView:
        world, prologue = build_scenario(theme, seed=seed)
        # Apply custom player name if given.
        if player_name and world.player_id is not None:
            player_comp = world.try_get(world.player_id, Player)
            if player_comp:
                player_comp.display_name = player_name
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = _Session(world=world, owner_id=owner_id)
        outcome = self._engine.apply(world, Action(ActionKind.LOOK))
        body = f"{prologue}\n\n{outcome.message}"
        narration = self._narrator.color(body, success=True)
        return self._view(
            session_id, world, narration, outcome, echo="", sounds=["intro"],
        )

    def load_world(self, world: World, owner_id: int | None) -> GameView:
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = _Session(world=world, owner_id=owner_id)
        outcome = self._engine.apply(world, Action(ActionKind.LOOK))
        body = f"You open your eyes back in {self._location(world)}.\n\n{outcome.message}"
        narration = self._narrator.color(body, success=True)
        return self._view(session_id, world, narration, outcome, echo="")

    def get_world(self, session_id: str, owner_id: int | None) -> World | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.owner_id is not None and session.owner_id != owner_id:
            return None
        return session.world

    # -- gameplay ----------------------------------------------------------

    def command(self, session_id: str, text: str, owner_id: int | None) -> GameView | None:
        session = self._sessions.get(session_id)
        if session is None or (
            session.owner_id is not None and session.owner_id != owner_id
        ):
            return None
        world = session.world
        result = self._parser.parse(text, world)

        # 1) Ambiguity — ask the player to disambiguate. No state change.
        if result.clarify:
            return self._view(
                session_id, world,
                self._narrator.color(result.clarify, success=False),
                Outcome.fail(OutcomeCode.INVALID, result.clarify), echo=text,
                sounds=["ui_error"],
            )

        # 2) Free-form — interpret, then apply engine-validated effects.
        if result.is_freeform:
            journal_before = len(world.journal)
            interpretation = self._interpreter.interpret(world, result.freeform or text)
            extra = apply_effects(world, interpretation.effects)
            # Deterministic safety net: authored discoveries surface whether or not the
            # LLM proposed them.
            extra += reveal_by_text(world, result.freeform or text)
            world.turn += 1
            quest_lines = self._engine.tick(world)
            body = "\n".join([interpretation.narration, *extra, *quest_lines]).strip()
            narration = self._narrator.color(body, success=True)
            outcome = Outcome.ok(body)
            sounds = ["type"]
            if len(world.journal) > journal_before:
                sounds.append("discover")
            if quest_lines:
                sounds.append("chime")
            return self._view(
                session_id, world, narration, outcome, echo=text,
                art_override=interpretation.art, sounds=sounds,
            )

        # 3) Canonical — the engine resolves it authoritatively.
        action = result.action
        assert action is not None
        outcome = self._engine.apply(world, action)
        quest_lines = self._engine.tick(world)
        message = outcome.message
        if quest_lines:
            message = message + "\n" + "\n".join(quest_lines)
        narration = self._narrator.color(message, success=outcome.success)
        return self._view(
            session_id, world, narration, outcome, echo=text,
            sounds=self._sounds_for(action, outcome, quest_lines),
        )

    # -- view assembly -----------------------------------------------------

    def _location(self, world: World) -> str:
        player = world.player_id
        assert player is not None
        name = world.try_get(world.get(player, Position).room_id, Name)
        return name.value if name else "the void"

    def _view(
        self,
        session_id: str,
        world: World,
        narration: str,
        outcome: Outcome,
        *,
        echo: str,
        art_override: str | None = None,
        sounds: list[str] | None = None,
    ) -> GameView:
        player = world.player_id
        assert player is not None
        room = world.get(world.get(player, Position).room_id, Room)
        location = self._location(world)

        return GameView(
            session_id=session_id,
            echo=echo,
            narration=narration,
            art=art_override,
            scene=room.scene,
            location=location,
            time=world.time_phase,
            weather=world.weather,
            exits=self._exits(world),
            ambience=room.ambience,
            sounds=sounds or [],
            player=self._player_view(world),
            inventory=self._inventory_view(world),
            equipped=self._equipped_view(world),
            entities=self._entities_view(world),
            quests=self._quest_view(world),
            journal=list(world.journal[-8:]),
            turn=world.turn,
            success=outcome.success,
            code=outcome.code.value,
        )

    def _exits(self, world: World) -> list[ExitView]:
        """Connections from the current room, with destination names once discovered."""
        player = world.player_id
        assert player is not None
        room = world.get(world.get(player, Position).room_id, Room)
        exits: list[ExitView] = []
        seen: set[str] = set()
        for direction, dest in room.exits.items():
            if direction in seen:
                continue
            seen.add(direction)
            dest_room = world.try_get(dest, Room)
            dest_name = world.try_get(dest, Name)
            discovered = bool(dest_room and dest_room.visited)
            exits.append(ExitView(
                direction=direction,
                to=dest_name.value if (discovered and dest_name) else "unknown",
                locked=direction in room.locked_exits,
            ))
        return sorted(exits, key=lambda e: e.direction)

    def _sounds_for(self, action: Action, outcome: Outcome, quest_lines: list[str]) -> list[str]:
        cues: list[str] = []
        if not outcome.success:
            cues.append("ui_error")
            return cues
        for event in outcome.events:
            if isinstance(event, DamageDealt) and event.amount > 0:
                cues.append("hit")
            elif isinstance(event, CombatantDefeated):
                cues.append("defeat")
        if action.kind is ActionKind.MOVE:
            cues.append("footstep")
        elif action.kind is ActionKind.UNLOCK:
            cues.append("unlock")
        elif action.kind in (ActionKind.TAKE, ActionKind.EQUIP):
            cues.append("pickup")
        if quest_lines:
            cues.append("chime")
        return cues or ["type"]

    def _player_view(self, world: World) -> PlayerView:
        player = world.player_id
        assert player is not None
        name = world.get(player, Name)
        display = world.try_get(player, Player)
        hp = world.get(player, Health)
        res = world.try_get(player, Resources) or Resources()
        prog = world.try_get(player, Progression) or Progression()
        attrs = world.try_get(player, Attributes) or Attributes()

        attribute_views = [
            AttributeView(name=label, value=value, modifier=attrs.modifier(value))
            for label, value in (
                ("STR", attrs.strength), ("DEX", attrs.dexterity),
                ("CON", attrs.constitution), ("INT", attrs.intelligence),
                ("WIS", attrs.wisdom), ("CHA", attrs.charisma),
            )
        ]
        return PlayerView(
            name=display.display_name if display else name.value,
            level=prog.level, exp=prog.exp, exp_next=prog.exp_next,
            attribute_points=prog.attribute_points,
            hp=hp.current, hp_max=hp.maximum,
            mp=res.mana, mp_max=res.mana_max,
            stamina=res.stamina, stamina_max=res.stamina_max,
            attributes=attribute_views,
        )

    def _inventory_view(self, world: World) -> list[ItemView]:
        player = world.player_id
        assert player is not None
        inventory = world.try_get(player, Inventory)
        if not inventory:
            return []
        views: list[ItemView] = []
        for item_id in inventory.items:
            item = world.get(item_id, Item)
            name = world.try_get(item_id, Name)
            views.append(ItemView(
                name=name.value if name else "?", icon=item.icon,
                rarity=item.rarity, quantity=item.quantity,
            ))
        return views

    def _equipped_view(self, world: World) -> list[ItemView]:
        player = world.player_id
        assert player is not None
        equipment = world.try_get(player, Equipment)
        if not equipment:
            return []
        views: list[ItemView] = []
        for item_id in equipment.slots.values():
            item = world.get(item_id, Item)
            name = world.try_get(item_id, Name)
            views.append(ItemView(
                name=name.value if name else "?", icon=item.icon,
                rarity=item.rarity, quantity=item.quantity, equipped=True,
            ))
        return views

    def _entities_view(self, world: World) -> list[EntityView]:
        """Non-hidden items and actors in the player's current room."""
        player = world.player_id
        assert player is not None
        room_id = world.get(player, Position).room_id
        views: list[EntityView] = []

        for eid in world.query(Item, Position):
            if world.get(eid, Position).room_id != room_id or world.has(eid, Hidden):
                continue
            name = world.try_get(eid, Name)
            item = world.get(eid, Item)
            if name:
                views.append(EntityView(glyph=item.icon, name=name.value, note="item"))

        for eid in world.query(Actor, Position):
            if world.get(eid, Position).room_id != room_id or world.has(eid, Hidden):
                continue
            name = world.try_get(eid, Name)
            actor = world.get(eid, Actor)
            note = "hostile" if actor.hostile else actor.faction
            if name:
                views.append(EntityView(glyph="!", name=name.value, note=note))
        return views

    def _quest_view(self, world: World) -> list[QuestView]:
        return [
            QuestView(
                name=q.name, completed=q.completed,
                objectives=[QuestObjectiveView(text=o.text, done=o.done) for o in q.objectives],
            )
            for q in world.quests
        ]

# A single process-wide service instance for the app.
game_service = GameService()
