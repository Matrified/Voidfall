"""The Narrator renders authoritative outcomes into ANSI-colored prose.

Canonical actions (move, take, attack) are narrated instantly from the engine's own
message — no AI, no latency. Free-form exploration is handled separately by
:class:`narration.interpreter.Interpreter`, which is where the LLM lives. This split keeps
mechanical play snappy while exploration stays rich.
"""

from __future__ import annotations

from ..domain.actions import Outcome
from .ansi import Palette, ansi


class Narrator:
    """Colorizes outcome text with the CRT palette."""

    def color_outcome(self, outcome: Outcome) -> str:
        return self.color(outcome.message, success=outcome.success)

    def color(self, prose: str, *, success: bool = True) -> str:
        if not success:
            return ansi(prose, Palette.YELLOW)
        head, _, tail = prose.partition("\n")
        head = ansi(head, Palette.BRIGHT_GREEN, Palette.BOLD)
        return f"{head}\n{tail}" if tail else head
