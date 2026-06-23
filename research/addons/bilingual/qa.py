"""Deterministic *candidate* parallel-QA flags built on the reference finder.

This is the infrastructure half: it produces review-only candidate flags (missing concept, agreement
mismatch) from alignment + feature comparison. The judgment half — confirming a flag, deciding
wrong-sense — is the skill layer ([[parallel-translation-qa]] / [[read-the-gate]]); these flags are
never auto-applied. Stdlib-only, deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .bidix import Bidix
from .finder import find_reference
from .stream import Token

# Apertium number tags we compare for agreement (extend via the param).
NUMBER_TAGS = frozenset({"sg", "pl", "du"})


@dataclass
class Flag:
    kind: str  # "missing_concept" | "agreement_mismatch"
    source_lemma: str
    detail: str
    confidence: float
    target_surface: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    review_only: bool = True


def assess(
    source_tokens: list[Token],
    target_tokens: list[Token],
    bidix: Bidix,
    *,
    number_tags: frozenset[str] = NUMBER_TAGS,
    provenance: dict[str, Any] | None = None,
) -> list[Flag]:
    """Emit deterministic candidate flags for a source/target sentence pair."""
    prov = dict(provenance or {})
    flags: list[Flag] = []
    for tok in source_tokens:
        if not tok.analyses:
            continue
        src = tok.analyses[0]
        corr = find_reference(src.lemma, target_tokens, bidix)
        if not corr.found:
            flags.append(
                Flag(
                    kind="missing_concept",
                    source_lemma=src.lemma,
                    detail=f"source concept '{src.lemma}' has no realization in the target",
                    confidence=0.6,
                    provenance=prov,
                )
            )
            continue
        src_num = set(src.tags) & number_tags
        for m in corr.matches:
            tgt_num = set(m.tags) & number_tags
            if src_num and tgt_num and src_num.isdisjoint(tgt_num):
                flags.append(
                    Flag(
                        kind="agreement_mismatch",
                        source_lemma=src.lemma,
                        target_surface=m.surface,
                        detail=f"number mismatch: source {sorted(src_num)} vs target {sorted(tgt_num)}",
                        confidence=0.7,
                        provenance=prov,
                    )
                )
    return flags
