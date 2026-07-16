"""Selectable story scenarios.

Each scenario builds a complete, self-contained world through the same ECS — different
setting, tone, rooms, items, foes, and quests — and returns it alongside an opening
prologue. This is how the main menu offers "choose your story".
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
from .world_seed import build_world

# --- shared helpers -------------------------------------------------------


def _item(world: World, name: str, aliases, desc: str, **kw) -> int:
    eid = world.spawn()
    world.add(eid, Name(name, aliases=tuple(aliases)))
    world.add(eid, Description(desc))
    world.add(eid, Item(**kw))
    return eid


def _make_player(world: World, name: str, room_id: int) -> int:
    player = world.spawn()
    world.add(player, Player(display_name=name))
    world.add(player, Name("you"))
    world.add(player, Position(room_id=room_id))
    world.add(player, Health(current=120, maximum=140))
    world.add(player, Resources(mana=60, mana_max=80, stamina=70, stamina_max=100))
    world.add(player, Progression(level=8, exp=1200, exp_next=2400))
    world.add(player, Attributes(strength=14, dexterity=13, constitution=14,
                                 intelligence=12, wisdom=11, charisma=11))
    world.add(player, Stats(attack=7, defense=2, speed=3))
    world.add(player, Inventory(capacity=16))
    world.add(player, Equipment())
    world.player_id = player
    return player


# --- undead: The Hollow Harvest -------------------------------------------


def _build_undead(seed: int) -> World:
    world = World(rng=Rng(seed=seed), seed=seed, weather="Fog", clock=1080)

    square = world.spawn()
    world.add(square, Name("Ashford Square"))
    world.add(square, Description(
        "The plague village of Ashford lies silent under a grey fog. Doors hang open. "
        "A church looms north; a barricaded clinic waits east, its windows dark."
    ))
    world.add(square, Room(exits={}, visited=True, scene="village", ambience="wind"))

    church = world.spawn()
    world.add(church, Name("The Rotting Church"))
    world.add(church, Description(
        "Pews lie splintered. Something shuffles among the shadows of the nave, and the "
        "reek of the grave is thick here."
    ))
    world.add(church, Room(exits={}, scene="church", ambience="cave"))

    clinic = world.spawn()
    world.add(clinic, Name("The Barricaded Clinic"))
    world.add(clinic, Description(
        "Cots and dried bloodstains. Whoever fought the sickness here lost. But their "
        "records — and their cure — may remain."
    ))
    world.add(clinic, Room(exits={}, scene="clinic", ambience="wind"))

    world.get(square, Room).exits.update({"north": church, "east": clinic})
    world.get(square, Room).locked_exits["east"] = "the clinic door is nailed shut"
    world.get(church, Room).exits["south"] = square
    world.get(clinic, Room).exits["west"] = square

    crowbar = _item(world, "crowbar", ("bar", "iron bar"),
                    "A bent iron crowbar — good for prying nailed boards.",
                    portable=True, equippable=True, slot="hand", attack_bonus=4,
                    icon="key", is_key=True)
    world.add(crowbar, Position(room_id=square))

    _make_player(world, "Vale the Survivor", square)

    walker = world.spawn()
    world.add(walker, Name("shambling corpse", aliases=("corpse", "zombie", "walker", "thing")))
    world.add(walker, Description("A villager, weeks dead, still walking. Its jaw hangs wrong."))
    world.add(walker, Actor(hostile=True, faction="undead"))
    world.add(walker, Position(room_id=church))
    world.add(walker, Health(current=34, maximum=34))
    world.add(walker, Stats(attack=6, defense=1, speed=1))

    cure = _item(world, "vial of antitoxin", ("vial", "cure", "antitoxin", "serum"),
                 "A sealed vial of amber serum — the physician's last work.",
                 portable=True, icon="potion", rarity="epic")
    world.add(cure, Position(room_id=clinic))
    world.add(cure, Hidden(
        keywords=("cabinet", "records", "desk", "drawer", "shelf", "cure", "serum"),
        reveal_note="In a locked cabinet you find the physician's antitoxin — the cure.",
        set_flag="found_cure",
    ))

    world.quests = [
        Quest(id="the_cure", name="The Hollow Harvest", objectives=[
            Objective("Recover the physician's antitoxin", flag="found_cure"),
        ]),
    ]
    return world


_UNDEAD_PROLOGUE = (
    "The fog came first. Then the coughing. Then the dead got up and walked.\n"
    "You are the last of Ashford still breathing, and somewhere in this village is the "
    "cure the physician died protecting. Find it — before the harvest takes you too.\n\n"
    "Say what you do in plain words — \"pry open the clinic\", \"search the cabinet\", "
    "\"smash the corpse\" — and the world answers."
)


# --- starship: The Derelict Aurora ----------------------------------------


def _build_starship(seed: int) -> World:
    world = World(rng=Rng(seed=seed), seed=seed, weather="Vacuum", clock=0)

    bay = world.spawn()
    world.add(bay, Name("Docking Bay 7"))
    world.add(bay, Description(
        "Emergency lighting throbs red across the derelict starship Aurora. Your boots "
        "clang on the deck. A sealed blast door leads forward to the bridge; a maintenance "
        "shaft drops below."
    ))
    world.add(bay, Room(exits={}, visited=True, scene="ship", ambience="cave"))

    bridge = world.spawn()
    world.add(bridge, Name("The Silent Bridge"))
    world.add(bridge, Description(
        "Consoles flicker over frozen officers still strapped to their chairs. The main "
        "viewport shows a slow, wrong-colored star. The ship's core is close."
    ))
    world.add(bridge, Room(exits={}, scene="bridge", ambience="wind"))

    shaft = world.spawn()
    world.add(shaft, Name("Maintenance Shaft"))
    world.add(shaft, Description(
        "Cramped, humming with residual power. Something skitters in the dark beyond the "
        "reach of your light."
    ))
    world.add(shaft, Room(exits={}, scene="shaft", ambience="cave"))

    world.get(bay, Room).exits.update({"forward": bridge, "down": shaft})
    world.get(bay, Room).locked_exits["forward"] = "the blast door is magnetically sealed"
    world.get(bridge, Room).exits["back"] = bay
    world.get(shaft, Room).exits["up"] = bay

    log = world.spawn()
    world.add(log, Name("captain's final log", aliases=("log", "recording", "console", "data")))
    world.add(log, Description("A looping recording, the captain's voice frayed with static."))
    world.add(log, Item(portable=True, icon="scroll", rarity="epic"))
    world.add(log, Position(room_id=bridge))
    world.add(log, Hidden(
        keywords=("console", "log", "recording", "terminal", "captain", "data", "screen"),
        reveal_note=(
            "The captain's final log stutters to life: they opened something out past "
            "the dark star. Something that opened back."
        ),
        set_flag="found_log",
    ))

    keycard = _item(world, "command keycard", ("card", "keycard", "pass"),
                    "A senior officer's keycard, edges scorched.",
                    portable=True, icon="key", rarity="rare", is_key=True)
    world.add(keycard, Position(room_id=shaft))
    world.add(keycard, Hidden(
        keywords=("panel", "wires", "conduit", "body", "corpse", "toolbox", "hatch"),
        reveal_note="Behind a panel, clutched by a dead engineer, is a command keycard.",
        set_flag="found_keycard",
    ))

    _make_player(world, "Officer Renn", bay)
    world.get(world.player_id, Resources).mana_max = 0  # no magic in space

    xeno = world.spawn()
    world.add(xeno, Name("void-spawn", aliases=("alien", "creature", "xeno", "thing", "spawn")))
    world.add(xeno, Description("A chitinous horror unfolding too many limbs from the dark."))
    world.add(xeno, Actor(hostile=True, faction="xeno"))
    world.add(xeno, Position(room_id=shaft))
    world.add(xeno, Health(current=40, maximum=40))
    world.add(xeno, Stats(attack=7, defense=2, speed=3))

    world.quests = [
        Quest(id="reach_core", name="The Derelict Aurora", objectives=[
            Objective("Recover a command keycard", flag="found_keycard"),
            Objective("Play the captain's final log", flag="found_log"),
        ]),
    ]
    return world


_STARSHIP_PROLOGUE = (
    "The distress call stopped mid-word three days ago. Now you drift aboard the Aurora, "
    "and the only sounds are the ship's dying systems — and something else, moving.\n"
    "Reach the core. Find out what happened here. Try to leave.\n\n"
    "Speak plainly — \"pry the panel\", \"seal the door\", \"fire on the alien\" — and the "
    "ship answers."
)


# --- registry -------------------------------------------------------------

_MEDIEVAL_PROLOGUE = (
    "Cold rain needles your face as you climb the last of the broken road. Ahead, the "
    "shattered gate of Greyhelm Keep leans against a bruised sky — a place the maps forgot "
    "and the living avoid.\n"
    "You came chasing the lost heir and the caravan that never returned. Whatever waits "
    "inside has been waiting a long time.\n\n"
    "This world listens to plain words — \"search the broken cart\", \"push through the "
    "gate\", \"draw my blade\". Tell it what you do."
)

_SCENARIOS = {
    "medieval": (build_world, _MEDIEVAL_PROLOGUE),
    "undead": (_build_undead, _UNDEAD_PROLOGUE),
    "starship": (_build_starship, _STARSHIP_PROLOGUE),
}


def build_scenario(theme: str, seed: int = 1337) -> tuple[World, str]:
    """Return a fresh world and its prologue for the chosen theme."""
    builder, prologue = _SCENARIOS.get(theme, _SCENARIOS["medieval"])
    return builder(seed=seed), prologue
