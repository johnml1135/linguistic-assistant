"""Interchange types for a segmented, glossed word — the origin-agnostic input to the
grammar builder and the virtuous-cycle harness.

A :class:`MorphWord` is whatever an *ingester* produces: a surface form plus an ordered
list of (form, gloss) morphs. The gold origin is no longer a pre-annotated IGT corpus —
it comes from eBible parallel text + statistical word glosses (THOT HMM) and FieldWorks
data (see the `golden-pair-selection` work). Any such ingester just has to emit
``MorphWord``s; everything downstream (``grammar.build_model``, ``hc``, ``ablate``,
``score``) is independent of where they came from.

The SIGMORPHON-2023 IGT parser that used to live here was removed with that golden set;
only the interchange types remain.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Morph:
    """One aligned (form, gloss) pair inside a word."""

    form: str
    gloss: str
    #: boundary char that PRECEDED this morph ('' for the first, '-' affix or '=' clitic)
    boundary: str = ""


@dataclass
class MorphWord:
    """A single segmented word: its surface form and its ordered, glossed morphs."""

    surface: str
    morphs: list[Morph]

    @property
    def underlying(self) -> str:
        """Concatenation of morph forms — the wordform HermitCrab is asked to parse."""
        return "".join(m.form for m in self.morphs)

    @property
    def gold_analysis(self) -> list[tuple[str, str]]:
        """The (form, gloss) sequence a parse must reproduce."""
        return [(m.form, m.gloss) for m in self.morphs]
