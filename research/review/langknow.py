"""Per-language reference knowledge loader — the "derive don't hardcode" boundary.

The ALGORITHM (classes/agreement/project) must contain NO hardcoded linguistic facts. Language-specific
knowledge a corpus cannot fully derive (e.g. the Swahili inanimate-class prefix→class map — see
review.recover.derive_noun_class_map for the measured ceiling) lives as DATA in golden_sets/_reference/<lang>.json,
exactly like the gold sets and deltas: human/reference-provided, declarable, overridable, version-controllable.
This module loads it. Where the corpus CAN derive a fact, review.recover cross-checks the loaded value
(recovery_report: SM 8/9, ASSOC 5/5, prefix inventory 13/14) — so the data is verified, not merely trusted.

An unknown language with no reference file gets {} from every accessor — the engine then runs purely on what
projection + concord can derive, with no Bantu/Spanish facts leaking in.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_REF_DIR = Path(__file__).resolve().parents[1] / "golden_sets" / "_reference"


@lru_cache(maxsize=None)
def load(lang: str) -> dict:
    """The reference-knowledge dict for a language (by ISO code / pair key), or {} if none is provided."""
    if not lang:
        return {}
    key = lang.split("-")[0]                       # accept "swh" or "swh-onen…" pair keys
    p = _REF_DIR / f"{key}.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ── typed accessors (empty defaults → unknown languages derive everything, hardcode nothing) ──────────────
def noun_class_prefixes(lang: str) -> dict:
    return dict(load(lang).get("noun_class_prefixes", {}))


def meinhof_inventory(lang: str) -> list:
    return [tuple(row) for row in load(lang).get("meinhof_inventory", [])]


def class_prefix_set(lang: str) -> list:
    """The flat noun-class prefix inventory, longest-first (the string-match accelerator's prefix list)."""
    pres = {p for _cid, _name, ps in meinhof_inventory(lang) for p in ps}
    return sorted(pres, key=len, reverse=True)


def subject_markers(lang: str) -> list:
    return sorted(load(lang).get("subject_markers", []), key=len, reverse=True)


def subject_marker_to_class(lang: str) -> dict:
    return dict(load(lang).get("subject_marker_to_class", {}))


def tam_markers(lang: str) -> dict:
    return dict(load(lang).get("tam_markers", {}))


def object_markers(lang: str) -> list:
    return sorted(load(lang).get("object_markers", []), key=len, reverse=True)


def associative_markers(lang: str) -> set:
    return set(load(lang).get("associative_markers", []))


def associative_to_class(lang: str) -> dict:
    return dict(load(lang).get("associative_to_class", {}))


def possessive_stems(lang: str) -> tuple:
    return tuple(load(lang).get("possessive_stems", []))


def concord_prefixes(lang: str) -> set:
    return set(load(lang).get("concord_prefixes", []))


def function_words(lang: str) -> set:
    """Closed-class (non-content) tokens for a PIVOT language — used to tell a content-word alignment
    (candidate root) from a grammatical one. Reference data, loaded not hardcoded."""
    return set(load(lang).get("function_words", []))


def masculine_articles(lang: str) -> set:
    return set(load(lang).get("masculine_articles", []))


def feminine_articles(lang: str) -> set:
    return set(load(lang).get("feminine_articles", []))
