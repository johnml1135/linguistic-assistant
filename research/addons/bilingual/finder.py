"""Deterministic, morphology-aware reference finder.

source lemma -> bidix -> candidate vernacular lemma(s) -> locate the target token whose Hermit Crab
lemma matches, anywhere in the sentence. Lemma-level matching survives word order and inflection. No
Constraint Grammar, no statistical aligner — same inputs give the same result. Stdlib-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .bidix import Bidix
from .stream import Token


@dataclass
class Match:
    target_index: int
    surface: str
    lemma: str
    tags: tuple[str, ...]


@dataclass
class Correspondence:
    source_lemma: str
    found: bool
    matches: list[Match] = field(default_factory=list)


def find_reference(source_lemma: str, target_tokens: list[Token], bidix: Bidix) -> Correspondence:
    """Locate a source concept's realization(s) in the target token stream."""
    candidates = {lt[0] for lt in bidix.lookup_by_reference(source_lemma)}
    matches: list[Match] = []
    if candidates:
        for i, tok in enumerate(target_tokens):
            for a in tok.analyses:
                if a.lemma in candidates:
                    matches.append(Match(target_index=i, surface=tok.surface, lemma=a.lemma, tags=a.tags))
                    break  # one match per token is enough
    return Correspondence(source_lemma=source_lemma, found=bool(matches), matches=matches)


def find_all(source_tokens: list[Token], target_tokens: list[Token], bidix: Bidix) -> list[Correspondence]:
    """One Correspondence per source token (using its first analysis lemma)."""
    out: list[Correspondence] = []
    for tok in source_tokens:
        lemma = tok.analyses[0].lemma if tok.analyses else tok.surface
        out.append(find_reference(lemma, target_tokens, bidix))
    return out
