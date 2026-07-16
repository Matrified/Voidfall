"""Minimal ANSI styling helpers.

The frontend terminal (xterm.js) renders standard ANSI SGR sequences, so the backend can
speak color directly. We keep a tiny, named palette rather than scattering escape codes
through the codebase.
"""

from __future__ import annotations

from enum import Enum

_ESC = "\x1b["
_RESET = "\x1b[0m"


class Palette(str, Enum):
    """Named colors mapped to ANSI SGR foreground codes."""

    DIM = "2"
    BOLD = "1"
    GREEN = "32"
    CYAN = "36"
    YELLOW = "33"
    RED = "31"
    MAGENTA = "35"
    WHITE = "37"
    BRIGHT_GREEN = "92"


def ansi(text: str, *styles: Palette) -> str:
    """Wrap ``text`` in the given ANSI styles, always resetting afterwards."""
    if not styles:
        return text
    codes = ";".join(style.value for style in styles)
    return f"{_ESC}{codes}m{text}{_RESET}"
