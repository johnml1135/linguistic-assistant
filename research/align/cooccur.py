"""A dependency-free co-occurrence (Dice) aligner — the deterministic offline fallback + CI backend.

Not a replacement for THOT Eflomal on real data; it's a baseline that runs anywhere with no native
build, so the gloss pipeline and tests work offline. Deterministic.
"""

from __future__ import annotations

from collections import defaultdict

from .contract import Alignment, ParallelRow


def cooccur_align(rows: list[ParallelRow]) -> list[Alignment]:
    """Link each target token to the source token with the highest Dice co-occurrence across the corpus.

    Dice(s,t) = 2·cooc(s,t) / (count(s) + count(t)). Ties broken by lowest source index (stable).
    """
    cs: dict[str, int] = defaultdict(int)
    ct: dict[str, int] = defaultdict(int)
    cst: dict[tuple[str, str], int] = defaultdict(int)
    for src, tgt in rows:
        for s in set(src):
            cs[s] += 1
        for t in set(tgt):
            ct[t] += 1
        for s in set(src):
            for t in set(tgt):
                cst[(s, t)] += 1

    alignments: list[Alignment] = []
    for src, tgt in rows:
        links: Alignment = []
        for ti, t in enumerate(tgt):
            best_si, best_dice = -1, -1.0
            for si, s in enumerate(src):
                denom = cs[s] + ct[t]
                dice = (2 * cst[(s, t)] / denom) if denom else 0.0
                if dice > best_dice:  # strict > → first (lowest index) wins ties
                    best_dice, best_si = dice, si
            if best_si >= 0 and best_dice > 0.0:
                links.append((best_si, ti))
        alignments.append(links)
    return alignments
