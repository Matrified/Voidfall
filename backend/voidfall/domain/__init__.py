"""VOIDFALL domain layer — the pure, authoritative game engine.

This package has no dependency on the web framework, the database, or the LLM. It can be
imported and exercised in complete isolation, which is what makes it testable and what
keeps the AI firmly outside the game logic.
"""

from .actions import Action, ActionKind, Outcome, OutcomeCode
from .engine import Engine
from .world import World

__all__ = ["Action", "ActionKind", "Outcome", "OutcomeCode", "Engine", "World"]
