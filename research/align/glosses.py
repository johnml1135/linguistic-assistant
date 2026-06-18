"""Turn per-row alignment links into a GlossTable (deterministic)."""

from __future__ import annotations

from collections import defaultdict

from .contract import Alignment, CandidateGloss, GlossTable, ParallelRow


def build_gloss_table(rows: list[ParallelRow], alignments: list[Alignment]) -> GlossTable:
    """Aggregate alignment links across the corpus into ranked target->source glosses.

    ``prob`` is the link count for (target, source) normalized over all sources linked to that target.
    Sorting is by (-count, source_word) for stable, reproducible output.
    """
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (src, tgt), links in zip(rows, alignments):
        for s, t in links:
            if 0 <= s < len(src) and 0 <= t < len(tgt):
                counts[tgt[t]][src[s]] += 1

    table: dict[str, list[CandidateGloss]] = {}
    for target_word, src_counts in counts.items():
        total = sum(src_counts.values()) or 1
        cands = [
            CandidateGloss(target_word=target_word, source_word=s, prob=round(c / total, 4), count=c)
            for s, c in src_counts.items()
        ]
        cands.sort(key=lambda g: (-g.count, g.source_word))
        table[target_word] = cands
    return GlossTable(table=dict(sorted(table.items())))
