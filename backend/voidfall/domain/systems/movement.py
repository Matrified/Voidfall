"""Movement and unlocking.

Movement supports both precise directions ("north") and semantic intent resolved by the
parser ("enter the keep", "proceed inside") via ``Action.target_room``. Locked passages
stay locked until the player unlocks them with the right key — a real engine action, not
a line of flavor text.
"""

from __future__ import annotations

from ..actions import Action, Outcome, OutcomeCode
from ..components import Description, Inventory, Item, Name, Position, Resources, Room
from ..events import EntityMoved, EventBus, RoomEntered
from ..stats import force_stamina_cost
from ..world import World


def describe_room(world: World, room_id: int, *, brief: bool = False) -> str:
    """Compose the engine's description of a room (no mechanical 'Exits:' line)."""
    name = world.try_get(room_id, Name)
    desc = world.try_get(room_id, Description)
    if brief:
        return f"You return to {name.value if name else 'the room'}."
    if desc:
        return desc.text
    return name.value if name else "You look around."


def _direction_to(world: World, room: Room, destination: int) -> str | None:
    for direction, dest in room.exits.items():
        if dest == destination:
            return direction
    return None


def apply_move(world: World, action: Action, bus: EventBus) -> Outcome:
    """Resolve movement by direction or by a resolved target room."""
    assert world.player_id is not None
    player = world.player_id
    position = world.get(player, Position)
    room = world.get(position.room_id, Room)

    direction = action.direction
    # Semantic movement: the parser resolved a destination room; find its direction.
    if direction is None and action.target_room is not None:
        direction = _direction_to(world, room, action.target_room)

    if direction is None:
        return Outcome.fail(OutcomeCode.BLOCKED_MOVEMENT, "You cannot go that way.")

    if direction not in room.exits:
        return Outcome.fail(
            OutcomeCode.BLOCKED_MOVEMENT, f"There is no way {direction} from here."
        )

    if direction in room.locked_exits:
        condition = room.locked_exits[direction]
        return Outcome.fail(
            OutcomeCode.PASSAGE_BLOCKED,
            f"The way {direction} is blocked: {condition}. Perhaps it can be opened.",
        )

    destination = room.exits[direction]
    from_room = position.room_id
    world.set(player, Position(room_id=destination))

    dest_room = world.get(destination, Room)
    first_visit = not dest_room.visited
    if first_visit:
        dest_room.visited = True

    bus.publish(EntityMoved(player, from_room, destination))
    bus.publish(RoomEntered(player, destination, first_visit))
    return Outcome.ok(describe_room(world, destination, brief=not first_visit), tuple(bus.log))


def _has_unlock_tool(world: World) -> int | None:
    """Return an inventory item id that can open a lock: a key, or a forcing tool.

    An item qualifies if it is authored with ``Item.is_key=True`` (keys, crowbars,
    lockpicks, keycards — anything the content designer marks as a bypass tool) or if its
    name literally contains "key" as a convenience for unauthored content.
    """
    player = world.player_id
    assert player is not None
    inventory = world.try_get(player, Inventory)
    if not inventory:
        return None
    for item_id in inventory.items:
        item = world.try_get(item_id, Item)
        if item and item.is_key:
            return item_id
        name = world.try_get(item_id, Name)
        if name and "key" in name.value.lower():
            return item_id
    return None


def apply_unlock(world: World, action: Action, bus: EventBus) -> Outcome:
    """Unlock or force open a blocked passage using a key or tool from the inventory."""
    assert world.player_id is not None
    player = world.player_id
    room = world.get(world.get(player, Position).room_id, Room)

    if not room.locked_exits:
        return Outcome.fail(OutcomeCode.INVALID, "There is nothing here that needs opening.")

    tool_id = _has_unlock_tool(world)
    if tool_id is None:
        return Outcome.fail(
            OutcomeCode.NO_KEY,
            "It holds fast. You have nothing on hand that could open or force it.",
        )

    # Forcing something open costs stamina, reduced by Strength; too exhausted, it fails.
    cost = force_stamina_cost(world, player)
    resources = world.try_get(player, Resources)
    if resources and resources.stamina < cost:
        return Outcome.fail(
            OutcomeCode.INVALID,
            "Your arms shake with exhaustion. You have not the strength left to force it.",
        )
    if resources:
        resources.stamina = max(0, resources.stamina - cost)

    # Prefer the direction the player named; otherwise open the first locked way.
    direction = action.direction if action.direction in room.locked_exits else None
    if direction is None:
        direction = next(iter(room.locked_exits))

    room.locked_exits.pop(direction)
    tool_name = world.try_get(tool_id, Name)
    world.journal.append(f"You forced open the way {direction}.")
    return Outcome.ok(
        f"You work the {tool_name.value if tool_name else 'tool'} into the gap. With a "
        f"tortured groan of rusted metal and splintering wood, the way {direction} "
        f"gives way.",
        tuple(bus.log),
    )


def resolve_movement_target(world: World, nouns: list[str]) -> int | None:
    """Match free-form movement nouns to a connected room (by name/alias or intent)."""
    assert world.player_id is not None
    room = world.get(world.get(world.player_id, Position).room_id, Room)
    text = " ".join(nouns)

    # Direct room-name / alias match among connected rooms.
    for dest in room.exits.values():
        name = world.try_get(dest, Name)
        if name:
            labels = [name.value.lower(), *[a.lower() for a in name.aliases]]
            if any(label in text or text in label for label in labels if label):
                return dest

    # Intent words -> a sensible "forward" exit (prefer an unexplored way).
    forward_words = {
        "in", "inside", "forward", "ahead", "through", "onward", "on",
        "keep", "gate", "door", "deeper",
    }
    if any(w in forward_words for w in nouns):
        unexplored = [d for d in room.exits.values() if not _visited(world, d)]
        if unexplored:
            return unexplored[0]
        for pref in ("north", "in", "down", "east"):
            if pref in room.exits:
                return room.exits[pref]
        if room.exits:
            return next(iter(room.exits.values()))
    return None


def _visited(world: World, room_id: int) -> bool:
    room = world.try_get(room_id, Room)
    return bool(room and room.visited)
