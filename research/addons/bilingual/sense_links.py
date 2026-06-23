"""Cross-lingual sense links — the primary `bilingual/*` data — and building a bidix from them.

A sense link (the FLExTrans Sense Linker datum) ties a vernacular sense to a reference-language lemma.
The Apertium bidix is *derived* from these. Stdlib-only, deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .bidix import Bidix, BidixEntry
from .crosswalk import Crosswalk


@dataclass
class SenseLink:
    vernacular_lemma: str
    reference_lemma: str
    vernacular_tags: tuple[str, ...] = ()
    reference_tags: tuple[str, ...] = ()
    confidence: float | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


def from_change_set(ops: list[dict], crosswalk: Crosswalk | None = None) -> list[SenseLink]:
    """Read `bilingual.sense_link.add` ops (validated upstream) into SenseLinks.

    Op shape (see research/proposal/change_set.py + the cross-lingual-sense-link primitive):
      {"op":"bilingual.sense_link.add",
       "vernacular_sense": {"entry": "kondoo", "sense": 1, "pos": "Noun"},
       "reference_lemma":  {"lang": "eng", "lemma": "shepherd", "pos": "Noun"},
       "confidence": 0.7, "provenance": {...}}
    Project POS tags are mapped to Apertium tags via the crosswalk when supplied.
    """
    cw = crosswalk or Crosswalk()
    links: list[SenseLink] = []
    for op in ops:
        if op.get("op") != "bilingual.sense_link.add":
            continue
        vs = op.get("vernacular_sense") or {}
        rl = op.get("reference_lemma") or {}
        v_tags = _tags(vs.get("pos"), cw)
        r_tags = _tags(rl.get("pos"), cw)
        links.append(
            SenseLink(
                vernacular_lemma=str(vs.get("entry", "")),
                reference_lemma=str(rl.get("lemma", "")),
                vernacular_tags=v_tags,
                reference_tags=r_tags,
                confidence=op.get("confidence"),
                provenance=op.get("provenance") or {},
            )
        )
    return links


def _tags(pos: Any, cw: Crosswalk) -> tuple[str, ...]:
    if not pos:
        return ()
    mapped, _unmapped = cw.to_apertium([pos] if isinstance(pos, str) else list(pos))
    return tuple(mapped)


def build_bidix(links: list[SenseLink]) -> Bidix:
    """Derive a bidix from sense links (deduped)."""
    seen: set[tuple] = set()
    entries: list[BidixEntry] = []
    for ln in links:
        if not ln.vernacular_lemma or not ln.reference_lemma:
            continue
        key = (ln.reference_lemma, ln.reference_tags, ln.vernacular_lemma, ln.vernacular_tags)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            BidixEntry(
                reference=(ln.reference_lemma, ln.reference_tags),
                vernacular=(ln.vernacular_lemma, ln.vernacular_tags),
            )
        )
    return Bidix(entries=entries)
