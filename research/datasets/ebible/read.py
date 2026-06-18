"""Read eBible verse-per-line files into tokenized, verse-aligned parallel rows.

Pure functions operate on line lists (testable offline); file loaders wrap them. Tokenization uses
machine.py's LatinWordTokenizer when installed, else a Unicode-aware regex fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import NT_BOOKS

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_SKIP = {"", "<range>"}


def _tokenizer():
    try:
        from machine.tokenization import LatinWordTokenizer  # type: ignore

        tok = LatinWordTokenizer()
        return lambda s: [t for t in tok.tokenize(s) if _WORD_RE.fullmatch(t)]
    except Exception:
        return lambda s: _WORD_RE.findall(s)


def tokenize(text: str, *, lower: bool = True) -> list[str]:
    toks = _tokenizer()(text.lower() if lower else text)
    return toks


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
