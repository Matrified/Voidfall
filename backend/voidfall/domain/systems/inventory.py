"""Inventory and equipment systems.

Invariant: every item lives in exactly one container — a room's floor, the player's
inventory, or an equipment slot — never two at once. These functions preserve that
invariant and publish the corresponding change events.
"""

from __future__ import annotations

from ..actions import Action, Outcome, OutcomeCode
from ..components import Equipment, Inventory, Item, Name, Position
from ..events import EquipmentChanged, EventBus, InventoryChanged
from ..world import World


def _name_of(world: World, entity_id: int) -> str:
    name = world.try_get(entity_id, Name)
    return name.value if name else f"entity {entity_id}"


def _items_on_floor(world: World, room_id: int) -> list[int]:
    return [
        item
        for item in world.query(Item, Position)
        if world.get(item, Position).room_id == room_id
    ]


def apply_take(world: World, action: Action, bus: EventBus) -> Outcome:
    player = world.player_id
    assert player is not None
    item_id = action.target_id
    position = world.get(player, Position)

    if item_id is None or item_id not in _items_on_floor(world, position.room_id):
        return Outcome.fail(OutcomeCode.TARGET_NOT_FOUND, "You see no such thing here.")

    item = world.get(item_id, Item)
    if not item.portable:
        return Outcome.fail(
            OutcomeCode.NOT_PORTABLE, f"The {_name_of(world, item_id)} will not budge."
        )

    inventory = world.get(player, Inventory)
    if len(inventory.items) >= inventory.capacity:
        return Outcome.fail(
            OutcomeCode.CAPACITY_EXCEEDED, "You cannot carry any more."
        )

    world.remove(item_id, Position)
    inventory.items.append(item_id)
    bus.publish(InventoryChanged(player, item_id, added=True))
    return Outcome.ok(f"You take the {_name_of(world, item_id)}.", tuple(bus.log))


def apply_drop(world: World, action: Action, bus: EventBus) -> Outcome:
    player = world.player_id
    assert player is not None
    item_id = action.target_id
    inventory = world.get(player, Inventory)

    if item_id is None or item_id not in inventory.items:
        return Outcome.fail(OutcomeCode.TARGET_NOT_FOUND, "You are not carrying that.")

    position = world.get(player, Position)
    inventory.items.remove(item_id)
    world.set(item_id, Position(room_id=position.room_id))
    bus.publish(InventoryChanged(player, item_id, added=False))
    return Outcome.ok(f"You drop the {_name_of(world, item_id)}.", tuple(bus.log))


def apply_equip(world: World, action: Action, bus: EventBus) -> Outcome:
    player = world.player_id
    assert player is not None
    item_id = action.target_id
    inventory = world.get(player, Inventory)

    if item_id is None or item_id not in inventory.items:
        return Outcome.fail(OutcomeCode.TARGET_NOT_FOUND, "You are not carrying that.")

    item = world.get(item_id, Item)
    if not item.equippable or item.slot is None:
        return Outcome.fail(
            OutcomeCode.NOT_EQUIPPABLE, f"You cannot equip the {_name_of(world, item_id)}."
        )

    equipment = world.try_get(player, Equipment) or Equipment()
    # Return whatever occupied the slot to the inventory first.
    previous = equipment.slots.get(item.slot)
    if previous is not None:
        equipment.slots.pop(item.slot)
        inventory.items.append(previous)
        bus.publish(EquipmentChanged(player, previous, item.slot, equipped=False))

    inventory.items.remove(item_id)
    equipment.slots[item.slot] = item_id
    world.set(player, equipment)
    bus.publish(EquipmentChanged(player, item_id, item.slot, equipped=True))
    return Outcome.ok(f"You equip the {_name_of(world, item_id)}.", tuple(bus.log))


def apply_unequip(world: World, action: Action, bus: EventBus) -> Outcome:
    player = world.player_id
    assert player is not None
    item_id = action.target_id
    equipment = world.try_get(player, Equipment)

    slot = None
    if equipment:
        slot = next((s for s, i in equipment.slots.items() if i == item_id), None)
    if item_id is None or slot is None or equipment is None:
        return Outcome.fail(OutcomeCode.TARGET_NOT_FOUND, "You have not equipped that.")

    inventory = world.get(player, Inventory)
    if len(inventory.items) >= inventory.capacity:
        return Outcome.fail(OutcomeCode.CAPACITY_EXCEEDED, "Your hands are too full.")

    equipment.slots.pop(slot)
    inventory.items.append(item_id)
    bus.publish(EquipmentChanged(player, item_id, slot, equipped=False))
    return Outcome.ok(f"You remove the {_name_of(world, item_id)}.", tuple(bus.log))


def render_inventory(world: World) -> str:
    player = world.player_id
    assert player is not None
    inventory = world.get(player, Inventory)
    equipment = world.try_get(player, Equipment)

    lines = ["You are carrying:"]
    if inventory.items:
        lines += [f"  - {_name_of(world, i)}" for i in inventory.items]
    else:
        lines.append("  (nothing)")
    if equipment and equipment.slots:
        lines.append("Equipped:")
        for slot, item_id in sorted(equipment.slots.items()):
            lines.append(f"  - {slot}: {_name_of(world, item_id)}")
    return "\n".join(lines)
