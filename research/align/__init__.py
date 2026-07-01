"""Statistical word-gloss alignment — a probabilistic source of word glosses (THOT Eflomal via
sil-machine, with a dependency-free co-occurrence fallback). Complements the deterministic Apertium
bidix; output feeds candidate `bilingual/*` sense links.
"""

from __future__ import annotations

from .aligner import align
from .contract import Alignment, CandidateGloss, GlossTable, ParallelRow
from .glosses import build_gloss_table
from .to_bilingual import gloss_table_to_sense_link_ops

__all__ = [
    "align",
    "build_gloss_table",
    "gloss_table_to_sense_link_ops",
    "GlossTable",
    "CandidateGloss",
    "ParallelRow",
    "Alignment",
]
