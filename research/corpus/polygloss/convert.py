"""Convert PolyGloss corpus rows into this repo's existing IGT interchange types.

A row's `segmentation`/`glosses` are whitespace-separated per word and `-`/`=`-separated per morph
within a word — the same boundary convention `engine/igt.py::Morph.boundary` already uses. So a row
converts losslessly into a list of `MorphWord`s; no new interchange type is needed.

Leipzig Glossing Rules convention: grammatical category labels are capitalized (`ART`, `1SG`, `PL`);
lexical glosses are lowercase, often dotted for multi-word translations (`you.know`). We use that
convention to split each word's morphs into a stem (lemma-bearing) morph and grammatical morphs
(feature-bearing) — see `is_grammatical_gloss`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from align.contract import ParallelRow  # noqa: E402
from corpus.ebible.read import tokenize  # noqa: E402
from engine.igt import Morph, MorphWord  # noqa: E402

from .schema import PolyglossRow  # noqa: E402

_BOUNDARY_RE = re.compile(r"[-=]")


def _split_word(seg_word: str, gloss_word: str) -> MorphWord | None:
    """One (segmented-word, glossed-word) pair -> a MorphWord. None if morph counts disagree
    (misaligned rows exist in the corpus — the paper's own audit found ~34,894 of them)."""
    # Boundary chars are separators; keep them by splitting on a capturing group.
    seg_parts = re.split(r"([-=])", seg_word)
    gloss_parts = re.split(r"([-=])", gloss_word)
    if len(seg_parts) != len(gloss_parts):
        return None
    morphs: list[Morph] = []
    boundary = ""
    for seg_tok, gloss_tok in zip(seg_parts, gloss_parts):
        if seg_tok in ("-", "="):
            if seg_tok != gloss_tok:
                return None  # boundary mismatch between the two tiers
            boundary = seg_tok
            continue
        morphs.append(Morph(form=seg_tok, gloss=gloss_tok, boundary=boundary))
        boundary = ""
    if not morphs:
        return None
    return MorphWord(surface="".join(m.form for m in morphs), morphs=morphs)


def to_morphwords(row: PolyglossRow) -> list[MorphWord]:
    """A segmented+glossed row -> one MorphWord per word. Skips words whose segmentation/gloss
    tiers don't line up (see `_split_word`) rather than guessing."""
    if not row.is_segmented:
        return []
    seg_words = row.segmentation.split()
    gloss_words = row.glosses.split()
    if len(seg_words) != len(gloss_words):
        return []  # whole-row tier mismatch — not usable
    out = []
    for sw, gw in zip(seg_words, gloss_words):
        mw = _split_word(sw, gw)
        if mw is not None:
            out.append(mw)
    return out


_GRAMMATICAL_RE = re.compile(r"^[A-Z0-9](?:[A-Z0-9._]*[A-Z0-9])?$")


def is_grammatical_gloss(tag: str) -> bool:
    """Leipzig convention: grammatical labels are all-caps (`ART`, `1SG`, `PL`, `ZERO`); lexical
    glosses are lowercase (`garden`, `you.know`). `0` (zero morph) counts as grammatical."""
    return tag == "0" or bool(_GRAMMATICAL_RE.match(tag)) and tag.upper() == tag


def stem_and_features(word: MorphWord) -> tuple[Morph | None, list[str]]:
    """Split a word's morphs into its lemma-bearing stem (first non-grammatical morph, if any) and
    the ordered list of grammatical-morph glosses (the word's feature bundle, simplified — see
    Polygloss_integration.md §4.2 for why this isn't yet `gold/inflection.py::canon()`-compatible)."""
    stem: Morph | None = None
    features: list[str] = []
    for m in word.morphs:
        if is_grammatical_gloss(m.gloss):
            features.append(m.gloss)
        elif stem is None:
            stem = m
        else:
            features.append(m.gloss)  # a second lexical-looking morph — keep, don't drop data
    return stem, features


def is_english_metalanguage(row: PolyglossRow) -> bool:
    """English-metalanguage rows reuse the pivot-language assumptions already baked into the
    eBible tokenizer choice; see Polygloss_integration.md §5, criterion 2."""
    return row.metalanguage.strip().lower() == "english"


def to_parallel_row(row: PolyglossRow, *, extra_word_chars: str = "") -> ParallelRow:
    """(translation_tokens, transcription_tokens) — the pivot ("source") side is the metalanguage
    translation, the induced ("target") side is the object-language transcription, matching the
    `(src, tgt)` convention `corpus/ebible/read.py::VerseRow` already uses.

    `extra_word_chars` (see `corpus/polygloss/orthography.py`) only applies to the transcription
    (target-language) side — it's a target-orthography exception, not a pivot/English one."""
    return tokenize(row.translation), tokenize(row.transcription, extra_word_chars=extra_word_chars)
