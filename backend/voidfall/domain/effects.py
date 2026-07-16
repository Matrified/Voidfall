"""Sanctioned world effects.

Free-form actions let a player type anything. The LLM interprets intent and *proposes*
effects, but it may only propose from this fixed vocabulary, and the engine validates and
clamps every one before applying it. This is the hard boundary that keeps the world
consistent: the AI narrates, the engine decides.

An effect that fails validation is silently dropped — the narration still shows, but the
world does not change in an unsanctioned way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .components import Actor, Attributes, Hidden, Name, Position
from .world import World

# Bounds that cap how much a single free-form action can move the needle.
MAX_HEAL = 8
MAX_HURT = 8
MAX_REP_DELTA = 5
MAX_STAMINA_RESTORE = 15


@dataclass(frozen=True, slots=True)
class Effect:
    kind: str
    payload: dict[str, Any]


def _reveal(world: World, keyword: str) -> str | None:
    """Reveal a hidden entity in the current room matching ``keyword``."""
    assert world.player_id is not None
    room_id = world.get(world.player_id, Position).room_id
    keyword = keyword.lower().strip()
    for eid in world.query(Hidden, Position):
        if world.get(eid, Position).room_id != room_id:
            continue
        hidden = world.get(eid, Hidden)
        if any(keyword == k or keyword in k for k in hidden.keywords):
            note = hidden.reveal_note
            flag = hidden.set_flag
            world.remove(eid, Hidden)  # now visible to listings
            name = world.try_get(eid, Name)
            world.journal.append(note or f"You discovered {name.value if name else 'something'}.")
            if flag:
                world.flags[flag] = True  # advances any quest keyed to this flag
            return note or None
    return None


def _reputation(world: World, faction: str, delta: int) -> str | None:
    delta = max(-MAX_REP_DELTA, min(MAX_REP_DELTA, int(delta)))
    if delta == 0:
        return None

    # Charisma sharpens social outcomes: a silver tongue amplifies both praise and scorn.
    assert world.player_id is not None
    attrs = world.try_get(world.player_id, Attributes)
    if attrs:
        cha_mod = attrs.modifier(attrs.charisma)
        delta += cha_mod if delta > 0 else -abs(cha_mod)
        delta = max(-MAX_REP_DELTA - 3, min(MAX_REP_DELTA + 3, delta))

    key = f"rep:{faction.lower()}"
    current = int(world.flags.get(key, 0)) if isinstance(world.flags.get(key), int) else 0
    new = max(-100, min(100, current + delta))
    world.flags[key] = new  # type: ignore[assignment]
    direction = "improves" if delta > 0 else "sours"
    return f"Your standing with {faction} {direction}."


# A keen mind (WIS modifier at or above this) catches a hidden thing from a related word,
# not just an exact keyword — e.g. noticing "the floor looks disturbed" is close enough to
# the authored keyword "flagstone" once you're perceptive enough to read the room.
_PERCEPTIVE_THRESHOLD = 1
_FUZZY_MIN_LEN = 4


def _keyword_hits(keyword: str, lowered: str, *, fuzzy: bool) -> bool:
    if keyword in lowered:
        return True
    if not fuzzy or len(keyword) < _FUZZY_MIN_LEN:
        return False
    # A sharp-eyed character notices a shared root even if the exact word differs
    # (e.g. "flagstone" vs. "floor stones") — a 4+ character prefix match is enough.
    prefix = keyword[:_FUZZY_MIN_LEN]
    return any(word.startswith(prefix) or prefix.startswith(word[:_FUZZY_MIN_LEN])
               for word in lowered.split() if len(word) >= _FUZZY_MIN_LEN)


def reveal_by_text(world: World, raw: str) -> list[str]:
    """Deterministically reveal any hidden thing the player's words touch.

    This runs on every free-form action regardless of the LLM, so authored discoveries are
    reliable: if you say "pry the flagstone" and something is hidden under a flagstone here,
    the engine surfaces it — the model does not get a vote on whether it exists.

    Wisdom raises perception: a character with a Wisdom modifier at or above
    ``_PERCEPTIVE_THRESHOLD`` also catches near-miss phrasing (a shared word root),
    not only an exact keyword match — a mechanical, felt benefit of a high-WIS build.
    """
    assert world.player_id is not None
    player = world.player_id
    room_id = world.get(player, Position).room_id
    lowered = raw.lower()

    attrs = world.try_get(player, Attributes)
    fuzzy = bool(attrs and attrs.modifier(attrs.wisdom) >= _PERCEPTIVE_THRESHOLD)

    notes: list[str] = []
    for eid in world.query(Hidden, Position):
        if world.get(eid, Position).room_id != room_id:
            continue
        hidden = world.get(eid, Hidden)
        if any(_keyword_hits(k, lowered, fuzzy=fuzzy) for k in hidden.keywords):
            note = _reveal(world, hidden.keywords[0])
            if note:
                notes.append(note)
    return notes


def apply_effects(world: World, effects: list[Effect]) -> list[str]:
    """Validate and apply proposed effects. Returns extra narration lines."""
    assert world.player_id is not None
    player = world.player_id
    from .components import Health  # local import avoids a cycle at module load

    lines: list[str] = []
    for effect in effects:
        payload = effect.payload
        match effect.kind:
            case "reveal":
                note = _reveal(world, str(payload.get("keyword", "")))
                if note:
                    lines.append(note)
            case "heal":
                amount = max(0, min(MAX_HEAL, int(payload.get("amount", 0))))
                if amount:
                    hp = world.get(player, Health)
                    hp.current = min(hp.maximum, hp.current + amount)
                    lines.append(f"You recover {amount} vitality.")
            case "hurt":
                amount = max(0, min(MAX_HURT, int(payload.get("amount", 0))))
                if amount:
                    hp = world.get(player, Health)
                    hp.current = max(0, hp.current - amount)
                    lines.append(f"You suffer {amount} harm.")
            case "reputation":
                line = _reputation(
                    world, str(payload.get("faction", "the locals")),
                    int(payload.get("delta", 0)),
                )
                if line:
                    lines.append(line)
            case "journal":
                text = str(payload.get("text", "")).strip()
                if text:
                    world.journal.append(text)
            case "flag":
                name = str(payload.get("name", "")).strip()
                if name:
                    world.flags[name] = True
            case "recover_stamina":
                from .components import Resources

                amount = max(0, min(MAX_STAMINA_RESTORE, int(payload.get("amount", 0))))
                res = world.try_get(player, Resources)
                if amount and res:
                    res.stamina = min(res.stamina_max, res.stamina + amount)
                    lines.append("You catch your breath.")
            case _:
                continue  # unknown effect kind -> dropped
    return lines


def visible_actor_summary(world: World) -> list[str]:
    """Names of non-hidden actors in the player's room (for prompts/UI)."""
    assert world.player_id is not None
    room_id = world.get(world.player_id, Position).room_id
    result: list[str] = []
    for eid in world.query(Actor, Position):
        if world.get(eid, Position).room_id == room_id and not world.has(eid, Hidden):
            name = world.try_get(eid, Name)
            if name:
                result.append(name.value)
    return result
