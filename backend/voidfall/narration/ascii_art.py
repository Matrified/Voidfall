"""ASCII scene art.

A hand-authored library keyed by a scene tag, so the main locations always render clean,
striking art. Free-form "focus" moments can additionally surface LLM-drawn art via the
interpreter. Art is intentionally colorless here; the frontend tints it with the CRT
palette.
"""

from __future__ import annotations

_GATE = r"""
        /\                     /\
       /  \     .-~~~~~-.     /  \
      /||  \   / _     _ \   /  ||\
     //||   \ | (o)   (o) | /   ||\\
    // ||    \|    ,___,    |/    || \\
   //  ||     \    '---'    /     ||  \\
  //   ||      '.._______..'      ||   \\
 //====||=================================||====\\
 |     ||   | [] |     | [] |   ||     |
 |     ||   |    |     |    |   ||     |
_|_____||___|____|_____|____|___||_____|_
        the ruined gate stands ajar
""".strip("\n")

_HALL = r"""
   ___     ___     ___     ___     ___
  |   |   |   |   |   |   |   |   |   |
  | | |   | | |   | | |   | | |   | | |
  |_|_|   |_|_|   |_._|   |_|_|   |_|_|
   |||     |||    . . .    |||     |||
   |||     |||   .  .  .   |||     |||
 ============================================
    broken pillars, and echoes that linger
""".strip("\n")

_CRYPT = r"""
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  ~   .   .-------.   .------.    .  ~
  ~       | R I P |   | RIP  |       ~
  ~   .   |_______|   |______|   .   ~
  ~~~~~~~~~~~~ still water ~~~~~~~~~~~~
        something breathes in the dark
""".strip("\n")

_SKULL = r"""
        .-----.
      .'  o o  '.
      |    ^    |
      |  \___/  |
       '.._____.'
""".strip("\n")

_LIBRARY: dict[str, str] = {
    "Ruins of Greyhelm": _GATE,
    "The Fallen Gate": _GATE,
    "Hall of Echoes": _HALL,
    "The Sunken Crypt": _CRYPT,
    "skull": _SKULL,
}


def art_for_location(location: str) -> str | None:
    """Return curated art for a named location, if any."""
    return _LIBRARY.get(location)


def art_for_tag(tag: str) -> str | None:
    return _LIBRARY.get(tag)
