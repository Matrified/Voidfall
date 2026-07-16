"""Provider contract.

Every provider exposes one method: turn a system + user prompt into text, optionally in
JSON mode. Providers must raise :class:`LLMUnavailable` on any failure (network, auth,
timeout, bad response) so the caller can fall back to the engine's own narration.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class LLMUnavailable(Exception):
    """Raised when a provider cannot fulfill a request for any reason."""


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def generate(self, system: str, user: str, *, json_mode: bool = False) -> str:
        """Return model text for the given prompts, or raise ``LLMUnavailable``."""
        ...
