"""Turn a GlossTable into *candidate* `bilingual/*` sense-link ops (low-confidence, skill-confirmed).

These are statistical candidates (provenance = the aligner) — the skill / human confirms them, and the
deterministic Apertium bidix path is the symbolic complement. Output ops validate against the
change-set contract in research/proposal/change_set.py.
"""

from __future__ import annotations

from .contract import GlossTable


def gloss_table_to_sense_link_ops(
    table: GlossTable,
    *,
    source_lang: str = "eng",
    min_prob: float = 0.5,
    min_count: int = 2,
    max_confidence: float = 0.6,
) -> list[dict]:
    """Emit `bilingual.sense_link.add` ops for confident gloss candidates only (review-required)."""
    ops: list[dict] = []
    for target_word, cands in table:
        top = cands[0] if cands else None
        if top is None or top.prob < min_prob or top.count < min_count:
            continue
        ops.append(
            {
                "op": "bilingual.sense_link.add",
                "vernacular_sense": {"entry": target_word},
                "reference_lemma": {"lang": source_lang, "lemma": top.source_word},
                # statistical candidate → bounded confidence; a skill/human confirms before commit
                "confidence": round(min(max_confidence, top.prob), 4),
                "provenance": {"source": "align/word-alignment", "count": top.count, "p": top.prob},
            }
        )
    return ops
