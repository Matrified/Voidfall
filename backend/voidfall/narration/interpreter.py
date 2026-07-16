"""Free-form action interpretation.

When a player types something outside the canonical verb set — "look in the crack",
"pray at the altar", "smell the air", "search the mud" — this module produces the
response. With an LLM configured it asks the model for immersive narration plus a set of
*proposed* effects drawn from the sanctioned vocabulary. Without one (or on failure) it
falls back to an engine-authored response that can still surface authored discoveries.

Whatever the source, the engine validates and applies the effects. The narrator here only
ever describes; it cannot change the world except through :mod:`domain.effects`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..domain.components import Attributes, Description, Hidden, Inventory, Name, Position, Room
from ..domain.effects import Effect, visible_actor_summary
from ..domain.world import World
from .providers import LLMProvider, LLMUnavailable

_SYSTEM_PROMPT = """\
You are the Narrator of VOIDFALL, a dark-fantasy text RPG. You describe the world in \
vivid, atmospheric second-person prose. You are NOT the game engine and you do NOT decide \
mechanics — you have zero authority to open locks, break barriers, defeat foes, or \
change the world in any permanent way. Follow these rules without exception:

1. The SCENE facts provided are the only truth. Never contradict them, never invent \
   exits, items, characters, or outcomes that conflict with them. If "locked_exits" \
   lists a blocked way, that way is NOT open — describe effort and failure, never success,
   even if the player insists or narrates their own success.
2. When the player searches, examines, or reaches into something, describe the effort and \
   the atmosphere but DO NOT state what (if anything) they find — the engine reveals \
   discoveries separately and authoritatively. Never name a specific found object.
3. Keep narration to 1-3 sentences. Evocative, grounded, concrete sensory detail over \
   flowery filler. Never repeat the room's base description verbatim.
4. You may propose EFFECTS only from this exact vocabulary; the engine validates each:
   - {"type":"reveal","keyword":"<noun>"}  when the player searches/examines and might \
     uncover something hidden (the engine checks if anything is actually there).
   - {"type":"journal","text":"<short lore note>"}  to record a discovery.
   - {"type":"reputation","faction":"<name>","delta":<-5..5>}  for social actions.
   - {"type":"heal","amount":<0..8>} or {"type":"hurt","amount":<0..8>} for minor, \
     clearly-justified effects (resting, touching something dangerous).
   - {"type":"recover_stamina","amount":<0..15>}  for a moment of respite or resolve.
   - {"type":"flag","name":"<snake_case>"}  to mark a story beat.
   If nothing should change, return an empty effects list.
5. The player's attributes are flavor context for HOW they act, not permission for WHAT \
   they can accomplish. A strong character describes force vividly; it does not mean a \
   locked door in "locked_exits" opens — only the engine's own unlock/force action does.
6. Optionally include small ASCII art (max 10 lines, <= 50 cols) in "art" ONLY when the \
   player focuses on a striking visual; otherwise use an empty string.

Respond with STRICT JSON: {"narration": string, "effects": array, "art": string}."""


@dataclass(slots=True)
class Interpretation:
    narration: str
    effects: list[Effect] = field(default_factory=list)
    art: str | None = None
    used_llm: bool = False


def build_scene(world: World, raw: str) -> dict:
    """Assemble a read-only snapshot of the current situation for the model."""
    assert world.player_id is not None
    player = world.player_id
    room_id = world.get(player, Position).room_id
    room = world.get(room_id, Room)
    name = world.try_get(room_id, Name)
    desc = world.try_get(room_id, Description)

    inventory = world.try_get(player, Inventory)
    carried = (
        [world.get(i, Name).value for i in inventory.items if world.try_get(i, Name)]
        if inventory
        else []
    )
    attrs = world.try_get(player, Attributes)

    return {
        "player_action": raw,
        "location": name.value if name else "unknown",
        "description": desc.text if desc else "",
        "exits": sorted(room.exits),
        "locked_exits": sorted(room.locked_exits),
        "present": visible_actor_summary(world),
        "carrying": carried,
        "time": world.time_phase,
        "weather": world.weather,
        "player_attributes": {
            "strength": attrs.strength, "dexterity": attrs.dexterity,
            "intelligence": attrs.intelligence, "wisdom": attrs.wisdom,
        } if attrs else {},
    }


def _coerce_effects(raw_effects: object) -> list[Effect]:
    effects: list[Effect] = []
    if not isinstance(raw_effects, list):
        return effects
    for item in raw_effects[:5]:  # cap effects per action
        if isinstance(item, dict) and isinstance(item.get("type"), str):
            kind = item["type"]
            payload = {k: v for k, v in item.items() if k != "type"}
            effects.append(Effect(kind=kind, payload=payload))
    return effects


def _parse_json(text: str) -> dict | None:
    """Extract a JSON object from a model response, tolerating code fences."""
    text = text.strip()
    fence = re.search(r"\{.*\}", text, re.DOTALL)
    candidate = fence.group(0) if fence else text
    try:
        data = json.loads(candidate)
        return data if isinstance(data, dict) else None
    except ValueError:
        return None


def _engine_fallback(world: World, raw: str) -> Interpretation:
    """A no-LLM response. Still lets authored discoveries surface via keywords."""
    assert world.player_id is not None
    room_id = world.get(world.player_id, Position).room_id
    lowered = raw.lower()

    # If the player's words touch a hidden thing here, propose its reveal.
    for eid in world.query(Hidden, Position):
        if world.get(eid, Position).room_id != room_id:
            continue
        hidden = world.get(eid, Hidden)
        if any(k in lowered for k in hidden.keywords):
            return Interpretation(
                narration="You focus your attention, and something reveals itself.",
                effects=[Effect("reveal", {"keyword": hidden.keywords[0]})],
            )

    # Otherwise, a grounded, non-committal beat that never fabricates state.
    return Interpretation(
        narration=(
            "You take a moment with that. Nothing here answers directly, but the "
            "world presses close and watchful."
        )
    )


class Interpreter:
    """Runs free-form actions through the LLM, or the engine fallback."""

    def __init__(self, provider: LLMProvider | None) -> None:
        self._provider = provider

    def interpret(self, world: World, raw: str) -> Interpretation:
        if self._provider is None:
            return _engine_fallback(world, raw)

        scene = build_scene(world, raw)
        user = json.dumps(scene, ensure_ascii=False)
        try:
            text = self._provider.generate(_SYSTEM_PROMPT, user, json_mode=True)
        except LLMUnavailable:
            return _engine_fallback(world, raw)

        data = _parse_json(text)
        if not data or not isinstance(data.get("narration"), str):
            return _engine_fallback(world, raw)

        art = data.get("art")
        return Interpretation(
            narration=data["narration"].strip(),
            effects=_coerce_effects(data.get("effects")),
            art=art.strip() if isinstance(art, str) and art.strip() else None,
            used_llm=True,
        )
