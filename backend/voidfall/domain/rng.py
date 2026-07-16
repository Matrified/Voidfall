"""Deterministic pseudo-random number generation.

The entire engine is deterministic: given the same world state, the same action, and
the same RNG seed and cursor, the engine must produce an identical result. Python's
``random`` module carries hidden global state and is therefore unsuitable. Instead we
use SplitMix64 — a tiny, fast, well-distributed generator whose entire state is a single
64-bit integer. That makes it trivially serializable and perfectly reproducible.

The ``cursor`` is simply the number of values drawn so far. Persisting ``(seed, cursor)``
lets us reconstruct the exact stream position after a save/load round-trip.
"""

from __future__ import annotations

from dataclasses import dataclass

_MASK64 = (1 << 64) - 1
_GOLDEN_GAMMA = 0x9E3779B97F4A7C15


def _mix64(z: int) -> int:
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9 & _MASK64
    z = (z ^ (z >> 27)) * 0x94D049BB133111EB & _MASK64
    return z ^ (z >> 31)


@dataclass(slots=True)
class Rng:
    """A deterministic, serializable random source.

    Attributes:
        seed: The immutable seed the stream was created from.
        cursor: How many values have been drawn. Advancing is the only mutation.
    """

    seed: int
    cursor: int = 0

    def _next_u64(self) -> int:
        self.cursor += 1
        state = (self.seed + self.cursor * _GOLDEN_GAMMA) & _MASK64
        return _mix64(state)

    def next_int(self, low: int, high: int) -> int:
        """Return an integer in the inclusive range ``[low, high]``."""
        if low > high:
            raise ValueError(f"invalid range: [{low}, {high}]")
        span = high - low + 1
        return low + self._next_u64() % span

    def next_float(self) -> float:
        """Return a float in ``[0.0, 1.0)`` with 53 bits of resolution."""
        return (self._next_u64() >> 11) / (1 << 53)

    def chance(self, probability: float) -> bool:
        """Return ``True`` with the given probability in ``[0.0, 1.0]``."""
        return self.next_float() < probability

    def clone(self) -> Rng:
        return Rng(self.seed, self.cursor)
