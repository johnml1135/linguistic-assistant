"""Curated word→gloss gold + a correctness gate for the TDD cycle.

The cycle's running gate is *coverage* (did the held-out form parse?). That is a cheap proxy, but
AGENTS.md wants **correctness** (did it parse to the RIGHT gloss?). This module adds that second,
stronger signal: a small **hand-verified** word→gloss set (independent of the noisy statistical
auto-glosses, so it actually catches gloss errors) scored against the induced grammar via the same
`hc` oracle. A gold entry is a hit when the grammar produces an analysis whose gloss line contains the
expected gloss token.

Gold lives in `cycle/gold/<pair>.jsonl` (one `{"word":..., "gloss":...}` per line); absent → no gate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RESEARCH))

from golden.grammar import LangModel  # noqa: E402
from golden.hc import run_parse  # noqa: E402

GOLD_DIR = Path(__file__).resolve().parent / "gold"


def load_gold(pair: str) -> list[tuple[str, str]]:
    """Load `cycle/gold/<pair>.jsonl` as [(word, gloss), ...]; [] if no gold file exists."""
    p = GOLD_DIR / f"{pair}.jsonl"
    if not p.exists():
        return []
    out: list[tuple[str, str]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        out.append((str(row["word"]).lower(), str(row["gloss"]).lower()))
    return out


def score_gold(model: LangModel, gold: list[tuple[str, str]],
               phon_feats: dict[str, dict[str, str]] | None = None, templated: bool = False,
               pos_aware: bool = False) -> dict:
    """Score the induced grammar against the gold: did each known word parse, and to the right gloss?

    `gold_recall` = fraction whose expected gloss token appears in SOME HC analysis (correctness).
    `gold_parsed` = fraction that produced any analysis (coverage on known vocabulary).
    Their gap is the signal the auto-glosses (or missing roots) are wrong, not just absent.
    """
    if not gold:
        return {"n": 0, "gold_recall": 0.0, "gold_parsed": 0.0, "missed": []}
    words = [w for w, _ in gold]
    parses = run_parse(model, words, chunk_size=25, chunk_timeout=20, templated=templated,
                       phon_feats=phon_feats, pos_aware=pos_aware)
    correct = parsed = 0
    missed: list[str] = []
    for word, gloss in gold:
        analyses = parses.get(word, [])
        if analyses:
            parsed += 1
        gloss_tokens = {tok.lower() for a in analyses for (_, tok) in a}
        if gloss in gloss_tokens:
            correct += 1
        else:
            missed.append(word)
    n = len(gold)
    return {
        "n": n,
        "gold_recall": round(correct / n, 4),
        "gold_parsed": round(parsed / n, 4),
        "missed": missed,
    }
