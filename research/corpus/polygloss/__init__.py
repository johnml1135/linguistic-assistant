"""PolyGloss-corpus ingestion for the blind-benchmark pilot. See ../Polygloss_integration.md."""

from __future__ import annotations

from .convert import (
    is_english_metalanguage,
    is_grammatical_gloss,
    stem_and_features,
    to_morphwords,
    to_parallel_row,
)
from .schema import PolyglossRow

__all__ = [
    "PolyglossRow",
    "to_morphwords",
    "to_parallel_row",
    "is_grammatical_gloss",
    "is_english_metalanguage",
    "stem_and_features",
]
