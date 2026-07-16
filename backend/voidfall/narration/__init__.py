"""Narration layer: turns authoritative outcomes into ANSI text.

The LLM lives here and only here, behind a boundary that forbids it from touching game
state. If no LLM is configured, or if it errors or times out, the engine's own message
is used verbatim, and free-form actions fall back to an engine-authored response.
"""

from . import ascii_art
from .ansi import Palette, ansi
from .interpreter import Interpretation, Interpreter
from .llm import Narrator
from .providers import build_provider

__all__ = [
    "Narrator",
    "Interpreter",
    "Interpretation",
    "build_provider",
    "ascii_art",
    "ansi",
    "Palette",
]
