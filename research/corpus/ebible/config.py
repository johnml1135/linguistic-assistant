"""Canonical eBible source IDs + NT book set for the golden-set pipeline.

The BibleNLP/ebible GitHub `corpus/` hosts only *redistributable* texts, each one verse per line and
aligned to the shared `metadata/vref.txt`. NT-only is fine for building the lexicon/grammar/statistical
model.

The targets below are chosen so each has an **open text** *and* a music-free, single-narrator audio
recording of the SAME translation available — the audio source audit (`research/audio/sources.py`)
gates download on exact-text-match + license, and these four are the ones that can plausibly satisfy it
(see `research/audio/sources/`). Swahili is the closest morphological analog to a vowel-harmony
agglutinative language; Indonesian/Tagalog bring Austronesian affixation; Spanish is the public-domain
end-to-end shakedown.
"""

from __future__ import annotations

RAW_BASE = "https://raw.githubusercontent.com/BibleNLP/ebible/main"
VREF_URL = f"{RAW_BASE}/metadata/vref.txt"
CORPUS_URL = RAW_BASE + "/corpus/{id}.txt"

# Reference (source) side: World English Bible (Protestant), public domain, full Bible.
# NB: the `eng-eng_web` / `eng-eng_kjv` / `eng-eng_asv` corpus files are empty stubs — use `eng-engwebp`.
ENGLISH_ID = "eng-engwebp"

# target key -> eBible corpus id (verified present in BibleNLP/ebible corpus/ on 2026-06-18).
TARGETS: dict[str, str] = {
    "swh": "swh-swhulb",     # Swahili (ULB) — Bantu: noun-class concord + verb-extension height harmony
    "ind": "ind-indags",     # Indonesian (Bible for All) — Austronesian: affix/circumfix, meN- nasal assim.
    "tgl": "tgl-tglulb",     # Tagalog (ULB) — Austronesian: infixation + reduplication, voice morphology
    "spa": "spa-spaRV1909",  # Spanish (Reina-Valera 1909) — fusional; public-domain end-to-end shakedown
    # text-only diversity set (no audio needed) — span morphological types the first four don't:
    "tur": "tur-turytc",     # Turkish — Turkic: agglutinative, VOWEL HARMONY, rich CASE, SOV
    "rus": "rus-russyn",     # Russian — Slavic: fusional, 6 CASES, free word order, Cyrillic (arb source was NT-sparse)
    "hin": "hin-hin2017",    # Hindi — Indo-Aryan: SOV, postpositions, gender + case + aspect
    "vie": "vie-vie1934",    # Vietnamese — Austroasiatic: ISOLATING (≈no morphology), tones (the other extreme)
}

# 27 New Testament books (USFM/vref 3-letter codes).
NT_BOOKS: frozenset[str] = frozenset(
    """MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM
    HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV""".split()
)
