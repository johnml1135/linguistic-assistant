"""Parse SIGMORPHON-2023 interlinear glossed text and align morphemes to glosses.

The shared-task format is line-prefixed blocks separated by blank lines::

    \\t <orthography>          surface words, space-separated
    \\m <segmentation>         morphemes; '-' affix boundary, '=' clitic boundary
    \\g <gloss>                glosses, aligned to \\m token-for-token
    \\l <translation>          free translation (matrix language)
    \\p <pos>                  word-level POS (some languages only)

We only need ``\\t``/``\\m``/``\\g``/``\\l`` here. The *uncovered* track-2 files carry
the full ``\\g`` and are the gold source; ``\\m`` is the segmentation we build the
underlying wordform from (see ``MorphWord.underlying``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

# A morpheme boundary is '-' (affix) or '=' (clitic). We keep which one it was so the
# emitter can model clitics distinctly later; v1 treats both as morpheme boundaries.
_BOUNDARY = re.compile(r"([-=])")


@dataclass(frozen=True)
class Morph:
    """One aligned (form, gloss) pair inside a word."""

    form: str
    gloss: str
    #: boundary char that PRECEDED this morph ('' for the first, '-' or '=' otherwise)
    boundary: str = ""


@dataclass
class MorphWord:
    """A single segmented word: its surface form and its aligned morphs."""

    surface: str
    morphs: list[Morph]

    @property
    def underlying(self) -> str:
        """Concatenation of morph forms — the wordform v1 asks HermitCrab to parse."""
        return "".join(m.form for m in self.morphs)

    @property
    def gold_analysis(self) -> list[tuple[str, str]]:
        """The (form, gloss) sequence the parse must reproduce."""
        return [(m.form, m.gloss) for m in self.morphs]


@dataclass
class IgtRecord:
    surface: str
    segmentation: str
    gloss: str
    translation: str
    words: list[MorphWord] = field(default_factory=list)


def _split_morphemes(token: str) -> list[tuple[str, str]]:
    """Split one space-delimited ``\\m`` token into (boundary, form) pieces.

    ``кун-й-ла`` -> [('', 'кун'), ('-', 'й'), ('-', 'ла')].
    """
    parts = _BOUNDARY.split(token)
    out: list[tuple[str, str]] = []
    boundary = ""
    for p in parts:
        if p in ("-", "="):
            boundary = p
            continue
        if p == "":
            continue
        out.append((boundary, p))
        boundary = ""
    return out


def align_word(seg_token: str, gloss_token: str) -> MorphWord | None:
    """Align one ``\\m`` token to its ``\\g`` token.

    Returns ``None`` when the morph/gloss counts disagree (a misaligned record we skip
    rather than guess at). Punctuation tokens (no glossable content) also return None.
    """
    morph_pieces = _split_morphemes(seg_token)
    gloss_pieces = [g for g in _BOUNDARY.split(gloss_token) if g not in ("-", "=", "")]
    if not morph_pieces:
        return None
    if len(morph_pieces) != len(gloss_pieces):
        return None
    morphs = [
        Morph(form=form, gloss=gloss, boundary=b)
        for (b, form), gloss in zip(morph_pieces, gloss_pieces)
    ]
    return MorphWord(surface=seg_token, morphs=morphs)


def parse_block(block: str) -> IgtRecord | None:
    """Parse one ``\\t/\\m/\\g/\\l`` block into an :class:`IgtRecord`."""
    fields: dict[str, str] = {}
    for line in block.splitlines():
        line = line.rstrip("\n")
        if len(line) >= 2 and line[0] == "\\":
            key, _, val = line[1:].partition(" ")
            fields[key] = val.strip()
    if "m" not in fields or "g" not in fields:
        return None
    seg_tokens = fields["m"].split()
    gloss_tokens = fields["g"].split()
    if not seg_tokens or len(seg_tokens) != len(gloss_tokens):
        return None
    words = []
    for s, g in zip(seg_tokens, gloss_tokens):
        w = align_word(s, g)
        if w is not None:
            words.append(w)
    return IgtRecord(
        surface=fields.get("t", ""),
        segmentation=fields["m"],
        gloss=fields["g"],
        translation=fields.get("l", ""),
        words=words,
    )


def parse_file(path: str | Path) -> list[IgtRecord]:
    """Parse a full SIGMORPHON glossing file into aligned records."""
    text = Path(path).read_text(encoding="utf-8")
    records = []
    for block in re.split(r"\n\s*\n", text):
        if not block.strip():
            continue
        rec = parse_block(block)
        if rec is not None and rec.words:
            records.append(rec)
    return records


def iter_words(records: list[IgtRecord]) -> Iterator[MorphWord]:
    for rec in records:
        yield from rec.words
