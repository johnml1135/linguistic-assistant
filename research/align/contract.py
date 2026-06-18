"""Types for statistical word-gloss alignment (a probabilistic complement to the Apertium bidix).

Stdlib-only. A ``GlossTable`` maps a target word to ranked candidate source (English) words with a
probability — these become *candidate* `bilingual/*` sense links for a skill/human to confirm.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# (source_tokens, target_tokens) for one verse/segment; tokens already lowercased/segmented.
ParallelRow = tuple[list[str], list[str]]

# Per-row alignment links: (source_index, target_index).
Alignment = list[tuple[int, int]]


@dataclass(frozen=True)
class CandidateGloss:
    target_word: str
    source_word: str
    prob: float  # P(source | target), normalized over the target word's candidates
    count: int  # co-occurrence/link count supporting it


@dataclass
class GlossTable:
    """target word -> candidate source glosses, each ranked by probability."""

    table: dict[str, list[CandidateGloss]] = field(default_factory=dict)

    def best(self, target_word: str) -> CandidateGloss | None:
        cands = self.table.get(target_word)
        return cands[0] if cands else None

    def __iter__(self):
        return iter(self.table.items())
