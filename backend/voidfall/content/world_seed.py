"""Builds the opening region of VOIDFALL — the Ruins of Greyhelm.

Hand-authored and deliberately dense: rooms with atmosphere, portable and equippable
items with rarity, a locked passage, a hostile creature, hidden things to discover through
free-form actions, and two starting quests. Everything is expressed through the ECS, so
procedural generation can extend the same world later.
"""

from __future__ import annotations

from ..domain.components import (
    Actor,
    Attributes,
    Description,
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
    Stats,
)
from ..domain.quests import Objective, Quest
from ..domain.rng import Rng
from ..domain.world import World


def _item(world: World, name: str, aliases, desc: str, **item_kwargs) -> int:
    eid = world.spawn()
    world.add(eid, Name(name, aliases=tuple(aliases)))
    world.add(eid, Description(desc))
    world.add(eid, Item(**item_kwargs))
    return eid


def build_world(seed: int = 1337) -> World:
    """Return a freshly seeded world with the player at the ruined gate."""
    world = World(rng=Rng(seed=seed), seed=seed, weather="Rain", clock=900)  # dusk, raining

    # --- Rooms -----------------------------------------------------------
    gate = world.spawn()
    world.add(gate, Name("Ruins of Greyhelm"))
    world.add(
        gate,
        Description(
            "The rain falls cold against your face. Ahead stands the ruined gate of "
            "Greyhelm Keep. A torn banner flutters in the wind. To the left, a broken "
            "cart lies half-buried in mud. The gate is slightly ajar."
        ),
    )
    world.add(gate, Room(exits={}, visited=True, scene="gate", ambience="rain"))

    hall = world.spawn()
    world.add(hall, Name("Hall of Echoes"))
    world.add(
        hall,
        Description(
            "Broken pillars line a vast hall. Your footsteps return to you a beat too "
            "late. A rusted door stands to the east; the way south returns to the gate."
        ),
    )
    world.add(hall, Room(
        exits={}, locked_exits={"east": "a heavy iron lock holds it fast"},
        scene="hall", ambience="wind",
    ))

    crypt = world.spawn()
    world.add(crypt, Name("The Sunken Crypt"))
    world.add(
        crypt,
        Description(
            "Water pools across a floor of carved names. Something breathes in the dark."
        ),
    )
    world.add(crypt, Room(exits={}, scene="crypt", ambience="cave"))

    wood = world.spawn()
    world.add(wood, Name("The Whispering Wood"))
    world.add(
        wood,
        Description(
            "Black pines crowd the path west of the gate. The rain barely reaches the "
            "ground here; instead it drips, slow and deliberate, from branch to branch. "
            "Something watched you the moment you stepped beneath the boughs."
        ),
    )
    world.add(wood, Room(exits={}, scene="forest", ambience="wind"))

    vault = world.spawn()
    world.add(vault, Name("The Sealed Vault"))
    world.add(
        vault,
        Description(
            "Behind the iron door, the air is dry and old. Gold light from your torch "
            "finds a chamber untouched by looters — and, on a bier at its center, the "
            "still form of the one you came to find."
        ),
    )
    world.add(vault, Room(exits={}, scene="vault", ambience="cave"))

    gate_room = world.get(gate, Room)
    gate_room.exits.update({"north": hall, "west": wood})
    world.get(hall, Room).exits.update({"south": gate, "down": crypt, "east": vault})
    world.get(crypt, Room).exits["up"] = hall
    world.get(wood, Room).exits["east"] = gate
    world.get(vault, Room).exits["west"] = hall

    # The heir rests in the vault — reaching them completes the main quest.
    heir = world.spawn()
    world.add(heir, Name("the sleeping heir", aliases=("heir", "noble", "figure", "body")))
    world.add(heir, Description("A young noble in funeral finery, impossibly preserved."))
    world.add(heir, Item(portable=False, icon="relic", rarity="legendary"))
    world.add(heir, Position(room_id=vault))
    world.add(heir, Hidden(
        keywords=("heir", "noble", "figure", "body", "bier", "form"),
        reveal_note=(
            "You approach the bier. It is the heir of Greyhelm — breathing, barely, "
            "under a sorcery older than the ruin. The bloodline is not ended after all."
        ),
        set_flag="found_heir",
    ))

    # --- Items -----------------------------------------------------------
    torch = _item(
        world, "torch", ("torches",), "A resin-soaked torch. It could hold a flame.",
        portable=True, equippable=True, slot="light", icon="torch",
        rarity="common", quantity=2,
    )
    world.add(torch, Position(room_id=gate))

    sword = _item(
        world, "longsword", ("sword", "blade", "longsword"),
        "A well-balanced longsword, its edge still keen.",
        portable=True, equippable=True, slot="hand", attack_bonus=6,
        icon="sword", rarity="uncommon",
    )
    world.add(sword, Position(room_id=hall))

    # --- Hidden discoveries (revealed via free-form actions) -------------
    key = _item(
        world, "iron key", ("key", "iron key"),
        "A heavy iron key, cold and pitted with rust.",
        portable=True, icon="key", rarity="rare", is_key=True,
    )
    world.add(key, Position(room_id=gate))
    world.add(
        key,
        Hidden(
            keywords=("cart", "mud", "wreck", "wheel"),
            reveal_note="Beneath the broken cart, half-sunk in mud, you find an iron key.",
        ),
    )

    coins = _item(
        world, "silver coins", ("coins", "silver", "money"),
        "A merchant's purse of tarnished silver — stamped with a caravan's mark.",
        portable=True, icon="coin", rarity="common", quantity=37,
    )
    world.add(coins, Position(room_id=crypt))
    world.add(
        coins,
        Hidden(
            keywords=("names", "floor", "grave", "stone", "carving", "flagstone"),
            reveal_note=(
                "Prying at a loose flagstone, you uncover a purse of silver stamped "
                "with the sigil of the lost caravan. So this is where it ended."
            ),
            set_flag="found_caravan",
        ),
    )

    # Hidden lore that advances the quests through exploration.
    remains = world.spawn()
    world.add(remains, Name("gatekeeper's remains", aliases=("bones", "skeleton", "body")))
    world.add(remains, Description("A watchman's bones, still clutching a rusted horn."))
    world.add(remains, Item(portable=False, icon="scroll", rarity="uncommon"))
    world.add(remains, Position(room_id=gate))
    world.add(remains, Hidden(
        keywords=("bones", "skeleton", "guard", "watchman", "gatekeeper", "body", "corpse"),
        reveal_note=(
            "Half-buried by the gate lie the bones of the old gatekeeper, a rusted "
            "horn still in his grip. Whatever he was warning of, no one answered."
        ),
        set_flag="met_gatekeeper",
    ))

    portrait = world.spawn()
    world.add(portrait, Name("faded portrait", aliases=("portrait", "painting", "mural")))
    world.add(portrait, Description("A water-stained portrait of a young noble."))
    world.add(portrait, Item(portable=False, icon="scroll", rarity="rare"))
    world.add(portrait, Position(room_id=hall))
    world.add(portrait, Hidden(
        keywords=("portrait", "painting", "wall", "fresco", "mural", "picture"),
        reveal_note=(
            "Behind curtains of grime hangs a portrait: a young heir of Greyhelm, "
            "eyes bright, a date of birth but no date of death. Where did they go?"
        ),
    ))

    # --- The player ------------------------------------------------------
    player = world.spawn()
    world.add(player, Player(display_name="Aric of the North"))
    world.add(player, Name("you"))
    world.add(player, Position(room_id=gate))
    world.add(player, Health(current=128, maximum=160))
    world.add(player, Resources(mana=74, mana_max=100, stamina=56, stamina_max=100))
    world.add(player, Progression(level=12, exp=2845, exp_next=3600))
    world.add(
        player,
        Attributes(strength=16, dexterity=14, constitution=15,
                   intelligence=11, wisdom=12, charisma=10),
    )
    world.add(player, Stats(attack=8, defense=3, speed=3))
    world.add(player, Inventory(capacity=16))
    world.add(player, Equipment())
    world.player_id = player

    starter = _item(
        world, "leather armor", ("armor", "leather"),
        "Supple, well-worn leather armor.",
        portable=True, equippable=True, slot="body", defense_bonus=3,
        icon="armor", rarity="common",
    )
    world.get(player, Inventory).items.append(starter)

    # --- A creature ------------------------------------------------------
    ghoul = world.spawn()
    world.add(ghoul, Name("pale ghoul", aliases=("ghoul", "creature", "thing", "figure")))
    world.add(ghoul, Description("A gaunt, grave-pale thing with too-long fingers."))
    world.add(ghoul, Actor(hostile=True, faction="undead"))
    world.add(ghoul, Position(room_id=crypt))
    world.add(ghoul, Health(current=42, maximum=42))
    world.add(ghoul, Stats(attack=6, defense=2, speed=2))

    # --- Quests ----------------------------------------------------------
    world.quests = [
        Quest(
            id="lost_heir",
            name="The Lost Heir",
            objectives=[
                Objective("Find the heir of Greyhelm Keep", flag="found_heir"),
                Objective("Speak to the gatekeeper", flag="met_gatekeeper"),
            ],
        ),
        Quest(
            id="missing_caravan",
            name="Missing Caravan",
            objectives=[
                Objective("Find the caravan that never arrived", flag="found_caravan"),
            ],
        ),
    ]

    return world
