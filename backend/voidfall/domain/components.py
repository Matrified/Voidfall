"""Component definitions for the Entity Component System.

A Component is a plain, typed data record describing a single aspect of an entity. It
holds *no behaviour* — logic lives in systems (see ``domain/systems``). Every component
is a frozen-friendly dataclass so the world can be copied and compared by value, which
is what makes determinism testable.

Components are registered in ``COMPONENT_REGISTRY`` by a stable string tag so the
serializer can round-trip them without relying on Python module paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Ordinal directions understood by the movement system.
DIRECTIONS = ("north", "south", "east", "west", "up", "down", "in", "out")


@dataclass(slots=True)
class Name:
    """Human-facing short name, plus alternate nouns the parser can match on."""

    value: str
    aliases: tuple[str, ...] = ()


@dataclass(slots=True)
class Description:
    """Long-form flavor text describing the entity."""

    text: str


@dataclass(slots=True)
class Position:
    """Which room entity this entity currently occupies."""

    room_id: int


@dataclass(slots=True)
class Room:
    """A location. ``exits`` maps a direction to a connected room id.

    ``locked_exits`` maps a direction to the name of an unmet passage condition; while
    present, that exit is blocked and the movement system reports the condition.
    """

    exits: dict[str, int] = field(default_factory=dict)
    locked_exits: dict[str, str] = field(default_factory=dict)
    visited: bool = False
    scene: str = "gate"      # scene-art key the UI renders for this room
    ambience: str = "wind"   # ambient sound bed for this room


@dataclass(slots=True)
class Health:
    """Current and maximum hit points."""

    current: int
    maximum: int


@dataclass(slots=True)
class Resources:
    """Secondary pools: mana and stamina."""

    mana: int = 0
    mana_max: int = 0
    stamina: int = 0
    stamina_max: int = 0


@dataclass(slots=True)
class Attributes:
    """The six core attributes, D&D-flavored, with derived modifiers."""

    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    def modifier(self, score: int) -> int:
        return (score - 10) // 2


@dataclass(slots=True)
class Progression:
    """Level and experience track."""

    level: int = 1
    exp: int = 0
    exp_next: int = 300
    attribute_points: int = 0  # unspent points earned from leveling up


@dataclass(slots=True)
class Stats:
    """Derived combat attributes."""

    attack: int = 1
    defense: int = 0
    speed: int = 1


@dataclass(slots=True)
class Inventory:
    """A container of item entity ids with a fixed capacity."""

    items: list[int] = field(default_factory=list)
    capacity: int = 10


@dataclass(slots=True)
class Item:
    """Marks an entity as a takeable item.

    An equippable item names its slot and the stat modifiers it grants while worn.
    ``icon`` and ``rarity`` are display hints for the UI (rarity tints the name).
    """

    portable: bool = True
    equippable: bool = False
    slot: str | None = None
    attack_bonus: int = 0
    defense_bonus: int = 0
    quantity: int = 1
    icon: str = "generic"  # semantic icon key mapped to a vector icon in the UI
    rarity: str = "common"  # common | uncommon | rare | epic | legendary
    is_key: bool = False    # authored flag: this item can unlock/force a passage


@dataclass(slots=True)
class Hidden:
    """Marks content the player has not discovered yet.

    Hidden entities are invisible to listings until an action reveals them. This is the
    engine's sanctioned surface for free-form discovery: the LLM may *reveal* what the
    author pre-placed, but it can never conjure something that was not here.

    ``keywords`` are the concepts that reveal it (e.g. "crack", "mud", "banner").
    """

    keywords: tuple[str, ...] = ()
    reveal_note: str = ""
    set_flag: str = ""  # optional world flag set when this is discovered (advances quests)


@dataclass(slots=True)
class Equipment:
    """Maps an equipment slot name to the equipped item entity id."""

    slots: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class Player:
    """Marker component identifying the player-controlled entity."""

    display_name: str = "wanderer"


@dataclass(slots=True)
class Actor:
    """Marks a non-player entity. ``hostile`` gates combat targeting."""

    hostile: bool = False
    faction: str = "neutral"


# Stable tag -> class. The serializer uses these tags, never Python paths.
COMPONENT_REGISTRY: dict[str, type] = {
    "Name": Name,
    "Description": Description,
    "Position": Position,
    "Room": Room,
    "Health": Health,
    "Resources": Resources,
    "Attributes": Attributes,
    "Progression": Progression,
    "Stats": Stats,
    "Inventory": Inventory,
    "Item": Item,
    "Hidden": Hidden,
    "Equipment": Equipment,
    "Player": Player,
    "Actor": Actor,
}

COMPONENT_TAGS: dict[type, str] = {cls: tag for tag, cls in COMPONENT_REGISTRY.items()}
