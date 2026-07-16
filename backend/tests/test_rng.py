"""The RNG must be deterministic and reproducible from (seed, cursor)."""

from voidfall.domain.rng import Rng


def test_same_seed_same_stream():
    a = Rng(seed=42)
    b = Rng(seed=42)
    assert [a.next_int(0, 100) for _ in range(50)] == [b.next_int(0, 100) for _ in range(50)]


def test_cursor_tracks_draws():
    rng = Rng(seed=7)
    rng.next_int(0, 10)
    rng.next_float()
    assert rng.cursor == 2


def test_resume_from_cursor():
    original = Rng(seed=99)
    first = [original.next_int(0, 1000) for _ in range(10)]

    # Reconstruct at the same cursor and continue; streams must align.
    resumed = Rng(seed=99, cursor=original.cursor)
    original_tail = [original.next_int(0, 1000) for _ in range(10)]
    resumed_tail = [resumed.next_int(0, 1000) for _ in range(10)]
    assert original_tail == resumed_tail
    assert first  # sanity


def test_range_bounds():
    rng = Rng(seed=1)
    for _ in range(1000):
        value = rng.next_int(5, 9)
        assert 5 <= value <= 9
