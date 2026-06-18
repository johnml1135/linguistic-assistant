"""Tiny verse-aligned fixture (English ↔ toy target) for offline alignment tests."""

from __future__ import annotations

from .contract import ParallelRow

# Crafted so co-occurrence (Dice) cleanly recovers: tanri↔god, sevgi↔love, dunya↔world.
FIXTURE_ROWS: list[ParallelRow] = [
    (["god", "love"], ["tanri", "sevgi"]),
    (["god", "world"], ["tanri", "dunya"]),
    (["love", "world"], ["sevgi", "dunya"]),
]
