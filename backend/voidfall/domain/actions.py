"""Engine actions and outcomes.

An ``Action`` is the structured, validated command the parser produces from free-form
text. The engine consumes actions and never raw strings. An ``Outcome`` is the result of
applying an action: whether it succeeded, a machine-readable code, an engine-authored
message, and the events it produced. The message is deterministic; the LLM may later
rephrase it, but the engine's message is the source of truth and the fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ActionKind(str, Enum):
    LOOK = "look"
    MOVE = "move"
    UNLOCK = "unlock"
    TAKE = "take"
    DROP = "drop"
    EQUIP = "equip"
    UNEQUIP = "unequip"
    ATTACK = "attack"
    INVENTORY = "inventory"
    WAIT = "wait"
    ALLOCATE = "allocate"


@dataclass(frozen=True, slots=True)
class Action:
    """A structured engine command.

    Attributes:
        kind: What the player wants to do.
        direction: For MOVE — the resolved direction.
        target_id: For actions on an entity — the resolved entity id.
        modifiers: Descriptive words that do not change the mechanics but are kept
            for the narrator to color the prose (e.g. "carefully", "while raising my
            sword").
        raw: The original player input, preserved verbatim.
    """

    kind: ActionKind
    direction: str | None = None
    target_id: int | None = None
    target_room: int | None = None  # for semantic movement ("enter the keep")
    target_attribute: str | None = None  # for ALLOCATE ("strength", "wisdom", ...)
    modifiers: tuple[str, ...] = ()
    raw: str = ""


# An outcome carries the events it produced; events are frozen Event instances.


class OutcomeCode(str, Enum):
    OK = "ok"
    BLOCKED_MOVEMENT = "blocked_movement"
    PASSAGE_BLOCKED = "passage_blocked"
    TARGET_NOT_FOUND = "target_not_found"
    NOT_PORTABLE = "not_portable"
    CAPACITY_EXCEEDED = "capacity_exceeded"
    NOT_EQUIPPABLE = "not_equippable"
    OUT_OF_RANGE = "out_of_range"
    NOT_A_COMBATANT = "not_a_combatant"
    LOCKED = "locked"
    NO_KEY = "no_key"
    NO_POINTS = "no_points"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class Outcome:
    """The engine's authoritative result of an action."""

    success: bool
    code: OutcomeCode
    message: str
    events: tuple[object, ...] = field(default_factory=tuple)

    @staticmethod
    def ok(message: str, events: tuple[object, ...] = ()) -> Outcome:
        return Outcome(True, OutcomeCode.OK, message, events)

    @staticmethod
    def fail(code: OutcomeCode, message: str) -> Outcome:
        return Outcome(False, code, message, ())
