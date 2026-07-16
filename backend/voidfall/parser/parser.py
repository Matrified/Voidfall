"""The parser turns free-form English into either a canonical :class:`Action` the engine
resolves directly, or a *free-form* request to be interpreted (see
:mod:`narration.interpreter`).

Design: the engine owns a small set of precise, cheat-proof verbs — move, take, drop,
equip, attack, and so on. Those resolve instantly with no AI. Anything else — "look in
the crack", "pray", "search the mud", "smell the air" — is not an error; it is a
free-form action the narrator interprets while the engine validates any consequences.

Descriptive modifiers ("carefully", "while keeping my sword raised") are always peeled off
and preserved so they can color the prose without changing the mechanics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..domain.actions import Action, ActionKind
from ..domain.components import Actor, Inventory, Item, Name, Position
from ..domain.systems.movement import resolve_movement_target
from ..domain.world import World

MAX_INPUT = 500

# Verbs that resolve to a precise engine action.
_VERBS: dict[str, ActionKind] = {
    "go": ActionKind.MOVE, "move": ActionKind.MOVE, "walk": ActionKind.MOVE,
    "run": ActionKind.MOVE, "head": ActionKind.MOVE, "travel": ActionKind.MOVE,
    "enter": ActionKind.MOVE, "proceed": ActionKind.MOVE, "advance": ActionKind.MOVE,
    "approach": ActionKind.MOVE, "climb": ActionKind.MOVE, "descend": ActionKind.MOVE,
    "cross": ActionKind.MOVE, "step": ActionKind.MOVE, "venture": ActionKind.MOVE,
    "unlock": ActionKind.UNLOCK, "open": ActionKind.UNLOCK, "unbar": ActionKind.UNLOCK,
    "force": ActionKind.UNLOCK, "pry": ActionKind.UNLOCK,
    "take": ActionKind.TAKE, "get": ActionKind.TAKE, "grab": ActionKind.TAKE,
    "pick": ActionKind.TAKE, "loot": ActionKind.TAKE, "collect": ActionKind.TAKE,
    "drop": ActionKind.DROP, "discard": ActionKind.DROP,
    "equip": ActionKind.EQUIP, "wield": ActionKind.EQUIP, "wear": ActionKind.EQUIP,
    "unequip": ActionKind.UNEQUIP, "sheathe": ActionKind.UNEQUIP,
    "attack": ActionKind.ATTACK, "hit": ActionKind.ATTACK, "strike": ActionKind.ATTACK,
    "kill": ActionKind.ATTACK, "fight": ActionKind.ATTACK, "slay": ActionKind.ATTACK,
    "inventory": ActionKind.INVENTORY, "inv": ActionKind.INVENTORY, "i": ActionKind.INVENTORY,
    "wait": ActionKind.WAIT, "rest": ActionKind.WAIT,
    "allocate": ActionKind.ALLOCATE, "improve": ActionKind.ALLOCATE,
    "train": ActionKind.ALLOCATE,
    # LOOK is special: bare look = engine; "look at X" = free-form examination.
    "look": ActionKind.LOOK, "l": ActionKind.LOOK,
}

# Strict compass/vertical directions: unambiguous, always resolved first.
_DIRECTION_ALIASES: dict[str, str] = {
    "n": "north", "s": "south", "e": "east", "w": "west", "u": "up", "d": "down",
    "north": "north", "south": "south", "east": "east", "west": "west",
    "up": "up", "down": "down",
}
# "in"/"out" are directional words too, but they are ambiguous with room names ("go in
# the clinic") — resolved only as a last-resort fallback, after semantic matching fails.
_LOOSE_DIRECTIONS = {"in": "in", "out": "out"}

_ADVERBS = {
    "carefully", "quietly", "slowly", "quickly", "cautiously", "silently",
    "boldly", "calmly", "warily", "swiftly", "gently", "stealthily", "slow",
}

_STOPWORDS = {"the", "a", "an", "at", "to", "with", "my", "some", "on", "of", "into"}

_CLAUSE_RE = re.compile(r"\b(while|as|keeping|holding|though|and then)\b.*$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ParseResult:
    """A parse outcome: a canonical action, a free-form request, or a clarification."""

    action: Action | None = None
    freeform: str | None = None
    clarify: str | None = None
    candidates: tuple[int, ...] = ()

    @property
    def ok(self) -> bool:
        return self.action is not None

    @property
    def is_freeform(self) -> bool:
        return self.freeform is not None


class Parser:
    """Stateless natural-language command parser."""

    def parse(self, text: str, world: World) -> ParseResult:
        raw = text
        stripped = text.strip()
        if not stripped:
            return ParseResult(clarify="Type what you want to do.")
        if len(stripped) > MAX_INPUT:
            stripped = stripped[:MAX_INPUT]

        lowered = stripped.lower()

        modifiers: list[str] = []
        clause = _CLAUSE_RE.search(lowered)
        if clause:
            modifiers.append(clause.group(0).strip())
            lowered = lowered[: clause.start()].strip()

        tokens = [t for t in re.split(r"\s+", lowered) if t]
        while tokens and tokens[0] in _ADVERBS:
            modifiers.append(tokens.pop(0))

        if not tokens:
            return ParseResult(freeform=raw)

        # A bare direction implies movement (compass/vertical, or plain "in"/"out").
        if len(tokens) == 1 and tokens[0] in _DIRECTION_ALIASES:
            return ParseResult(
                Action(ActionKind.MOVE, direction=_DIRECTION_ALIASES[tokens[0]],
                       modifiers=tuple(modifiers), raw=raw)
            )
        if len(tokens) == 1 and tokens[0] in _LOOSE_DIRECTIONS:
            return ParseResult(
                Action(ActionKind.MOVE, direction=_LOOSE_DIRECTIONS[tokens[0]],
                       modifiers=tuple(modifiers), raw=raw)
            )

        verb = tokens[0]
        kind = _VERBS.get(verb)
        if kind is None:
            return ParseResult(freeform=raw)  # unknown verb -> interpret freely

        rest = [t for t in tokens[1:] if t not in _STOPWORDS]

        if kind is ActionKind.MOVE:
            return self._parse_move(rest, modifiers, raw, world)
        if kind is ActionKind.UNLOCK:
            return self._parse_unlock(rest, modifiers, raw)
        if kind is ActionKind.ALLOCATE:
            return self._parse_allocate(rest, modifiers, raw)
        if kind in (ActionKind.INVENTORY, ActionKind.WAIT):
            return ParseResult(Action(kind, modifiers=tuple(modifiers), raw=raw))
        if kind is ActionKind.LOOK:
            # "look" / "look around" is a canonical room description; anything more
            # specific ("look in the crack") is a free-form examination.
            if not rest or rest == ["around"]:
                return ParseResult(Action(ActionKind.LOOK, modifiers=tuple(modifiers), raw=raw))
            return ParseResult(freeform=raw)

        return self._parse_targeted(kind, rest, modifiers, raw, world)

    # -- helpers -----------------------------------------------------------

    def _parse_move(
        self, rest: list[str], modifiers: list[str], raw: str, world: World
    ) -> ParseResult:
        # Unambiguous compass/vertical directions resolve immediately.
        for token in rest:
            if token in _DIRECTION_ALIASES:
                return ParseResult(
                    Action(ActionKind.MOVE, direction=_DIRECTION_ALIASES[token],
                           modifiers=tuple(modifiers), raw=raw)
                )
        # Semantic movement: "enter the clinic", "proceed inside", "cross the bridge" —
        # tried before the loose "in"/"out" words so a named destination always wins.
        target = resolve_movement_target(world, rest)
        if target is not None:
            return ParseResult(
                Action(ActionKind.MOVE, target_room=target, modifiers=tuple(modifiers), raw=raw)
            )
        # Fallback: bare "in"/"out" with no named destination.
        for token in rest:
            if token in _LOOSE_DIRECTIONS:
                return ParseResult(
                    Action(ActionKind.MOVE, direction=_LOOSE_DIRECTIONS[token],
                           modifiers=tuple(modifiers), raw=raw)
                )
        return ParseResult(freeform=raw)

    _ATTRIBUTE_NAMES = {
        "strength": "strength", "str": "strength",
        "dexterity": "dexterity", "dex": "dexterity",
        "constitution": "constitution", "con": "constitution",
        "intelligence": "intelligence", "int": "intelligence",
        "wisdom": "wisdom", "wis": "wisdom",
        "charisma": "charisma", "cha": "charisma",
    }

    def _parse_allocate(self, rest: list[str], modifiers: list[str], raw: str) -> ParseResult:
        field = None
        for token in rest:
            if token in self._ATTRIBUTE_NAMES:
                field = self._ATTRIBUTE_NAMES[token]
                break
        return ParseResult(
            Action(ActionKind.ALLOCATE, target_attribute=field,
                   modifiers=tuple(modifiers), raw=raw)
        )

    def _parse_unlock(self, rest: list[str], modifiers: list[str], raw: str) -> ParseResult:
        direction = None
        for token in rest:
            if token in _DIRECTION_ALIASES:
                direction = _DIRECTION_ALIASES[token]
                break
        return ParseResult(
            Action(ActionKind.UNLOCK, direction=direction, modifiers=tuple(modifiers), raw=raw)
        )

    def _parse_targeted(
        self, kind: ActionKind, rest: list[str], modifiers: list[str],
        raw: str, world: World,
    ) -> ParseResult:
        if not rest:
            return ParseResult(freeform=raw)

        noun = " ".join(rest)
        matches = self._resolve_target(noun, world)

        if not matches:
            return ParseResult(freeform=raw)  # nothing by that name -> interpret
        if len(matches) > 1:
            return ParseResult(
                clarify=f'Which "{noun}" do you mean?', candidates=tuple(matches)
            )
        return ParseResult(
            Action(kind, target_id=matches[0], modifiers=tuple(modifiers), raw=raw)
        )

    def _resolve_target(self, noun: str, world: World) -> list[int]:
        player = world.player_id
        assert player is not None
        room_id = world.get(player, Position).room_id

        candidates: set[int] = set()
        for eid in world.query(Position):
            if eid == player:
                continue
            if world.get(eid, Position).room_id == room_id and (
                world.has(eid, Item) or world.has(eid, Actor)
            ):
                candidates.add(eid)
        inventory = world.try_get(player, Inventory)
        if inventory:
            candidates.update(inventory.items)

        matches: list[int] = []
        for eid in sorted(candidates):
            name = world.try_get(eid, Name)
            if name is None:
                continue
            labels = (name.value.lower(), *(a.lower() for a in name.aliases))
            if any(noun == label or noun in label.split() for label in labels):
                matches.append(eid)
        return matches
