"""Canonical eBible source IDs + NT book set for the golden-set pipeline.

The BibleNLP/ebible GitHub `corpus/` hosts only *redistributable* texts, each one verse per line and
aligned to the shared `metadata/vref.txt`. Finnish is NOT hosted there (restricted); Hungarian (Uralic,
agglutinative, vowel harmony) is the closest available stand-in. NT-only is fine for building the
lexicon/grammar/statistical model.
"""

from __future__ import annotations

RAW_BASE = "https://raw.githubusercontent.com/BibleNLP/ebible/main"
VREF_URL = f"{RAW_BASE}/metadata/vref.txt"
CORPUS_URL = RAW_BASE + "/corpus/{id}.txt"

# Reference (source) side: World English Bible (Protestant), public domain, full Bible.
# NB: the `eng-eng_web` / `eng-eng_kjv` / `eng-eng_asv` corpus files are empty stubs — use `eng-engwebp`.
ENGLISH_ID = "eng-engwebp"

# target key -> eBible corpus id (verified present in the repo on 2026-06-17).
TARGETS: dict[str, str] = {
    "tur": "tur-turytc",  # Turkish — agglutinative, vowel harmony + consonant gradation
    "hun": "hun-hun",     # Hungarian — Uralic, heavy agglutination, vowel harmony (Finnish stand-in)
    # Finnish ("fin") is NOT in the redistributable corpus; add a source + id here to include it.
}

# 27 New Testament books (USFM/vref 3-letter codes).
NT_BOOKS: frozenset[str] = frozenset(
    """MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM
    HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV""".split()
)
