"""Read eBible verse-per-line files into tokenized, verse-aligned parallel rows.

Pure functions operate on line lists (testable offline); file loaders wrap them. Tokenization uses
machine.py's LatinWordTokenizer when installed, else a Unicode-aware regex fallback.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import NT_BOOKS

# Python's `\w` does NOT match Unicode MARK characters (categories Mn/Mc/Me) — Devanagari vowel signs
# (matras), the virama, Arabic harakat, combining diacritics. With a bare `\w+`, को (क+ो) tokenises to
# "क" and किताब shatters into ['क','त','ब'] — vowels dropped, words split. So we add the Mark categories
# as word-CONTINUATION characters. (BMP scan ≈ once at import; covers Devanagari/Arabic/Cyrillic/Thai/
# Hebrew/Latin-diacritic; supplementary-plane marks are negligible for these corpora.)
_MARKS = "".join(chr(c) for c in range(0x10000) if unicodedata.category(chr(c))[0] == "M")
_WORD_RE = re.compile(rf"\w[\w{re.escape(_MARKS)}]*", re.UNICODE)
_SKIP = {"", "<range>"}


@lru_cache(maxsize=None)
def _word_re(extra_word_chars: str) -> re.Pattern[str]:
    if not extra_word_chars:
        return _WORD_RE
    return re.compile(rf"\w[\w{re.escape(_MARKS)}{re.escape(extra_word_chars)}]*", re.UNICODE)


def tokenize(text: str, *, lower: bool = True, extra_word_chars: str = "") -> list[str]:
    r"""Script-AGNOSTIC word tokenizer. A token is a word char (`\w`) followed by any word chars OR
    Unicode combining MARKS — so Devanagari/Arabic/etc. keep their vowel signs instead of being shattered.
    Text is NFC-normalised first (composes decomposed Latin/Vietnamese). eBible is space-separated.

    `extra_word_chars`: additional literal characters to treat as word-continuation, for orthographies
    that use a character `\w`+marks doesn't cover as part of a word rather than as a boundary — e.g. a
    colon (Unicode category `Po`, punctuation) as a vowel-length mark in Cayuga (`"ahóhto:'"` is ONE
    word). Empty by default so every existing caller is unaffected; callers with a known per-language
    exception look it up themselves (see `corpus/polygloss/orthography.py`) rather than this general-
    purpose tokenizer hardcoding any language's quirks."""
    text = unicodedata.normalize("NFC", text)
    pattern = _word_re(extra_word_chars)
    return pattern.findall(text.lower() if lower else text)


@dataclass
class VerseRow:
    ref: str
    src: list[str]
    tgt: list[str]


def parallel_rows_from_lines(
    vref: list[str],
    src_lines: list[str],
    tgt_lines: list[str],
    *,
    nt_only: bool = True,
    lower: bool = True,
) -> list[VerseRow]:
    """Align by line index (shared vref); keep verses present (non-blank) on BOTH sides."""
    n = min(len(vref), len(src_lines), len(tgt_lines))
    rows: list[VerseRow] = []
    for i in range(n):
        ref = vref[i].strip()
        if nt_only and (not ref or ref.split()[0] not in NT_BOOKS):
            continue
        s_raw, t_raw = src_lines[i].strip(), tgt_lines[i].strip()
        if s_raw in _SKIP or t_raw in _SKIP:
            continue
        s, t = tokenize(s_raw, lower=lower), tokenize(t_raw, lower=lower)
        if s and t:
            rows.append(VerseRow(ref=ref, src=s, tgt=t))
    return rows


def _read_lines(path: str | Path) -> list[str]:
    return Path(path).read_text(encoding="utf-8").splitlines()


def parallel_rows(
    vref_path: str | Path,
    src_path: str | Path,
    tgt_path: str | Path,
    *,
    nt_only: bool = True,
    lower: bool = True,
) -> list[VerseRow]:
    return parallel_rows_from_lines(
        _read_lines(vref_path), _read_lines(src_path), _read_lines(tgt_path), nt_only=nt_only, lower=lower
    )
