"""Score an HC grammar's parses against PolyGloss-derived held-out gold.

Adapted from `gold/hc_validate.py::validate()` (parse-rate / lemma-recall / feature-recall), but
**not** a call into that module — it hardcodes `gold.hc_coverage._scripture_freqs(pair)` (eBible
scripture frequency) and validates `--pair` against `gold.compile.PAIR_DIR` (eBible-only pairs).
Neither applies to a PolyGloss-only pair, so this reimplements the same recall logic against
frequencies/gold computed directly from the PolyGloss rows themselves. See
`Polygloss_integration.md` §4 for why.

Split into a pure, HC-independent scoring function (`score_parses`, unit-testable offline) and a
thin driver (`score_pair`) that actually invokes Hermit Crab — only the latter needs the `hc` CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from gold.hc_coverage import _slug  # noqa: E402

# One HC analysis: an ordered list of (surface_morph, gloss) pairs, matching `engine.hc.run_parse`'s
# per-surface output shape (the same shape `gold/hc_validate.py` consumes).
Analysis = list[tuple[str, str]]


def score_parses(
    wordforms: list[dict],
    lemma_gloss: dict[str, str],
    parses: dict[str, list[Analysis]],
) -> dict:
    """`wordforms`: `{surface, lemma, features, ...}` records from `to_gold.rows_to_wordforms_and_lexicon`.
    `lemma_gloss`: lemma id -> its stem's gloss (the lexicon entry's `senses[0]`).
    `parses`: surface -> HC's analyses for it (empty/absent = unparsed).
    """
    n = len(wordforms)
    parsed = recalled = feat_ok = 0
    miss_parse: list[str] = []
    miss_lemma: list[str] = []
    miss_feat: list[str] = []
    for w in wordforms:
        analyses = parses.get(w["surface"]) or []
        if not analyses:
            miss_parse.append(w["surface"])
            continue
        parsed += 1
        expect = _slug(lemma_gloss.get(w["lemma"]))

        def has_lemma(a: Analysis) -> bool:
            return any(g == expect or g.startswith(expect + "|") for _, g in a)

        if any(has_lemma(a) for a in analyses):
            recalled += 1
        else:
            miss_lemma.append(f"{w['surface']}->{w['lemma']}")
            continue
        expected_feats = set(w.get("features") or [])
        if not expected_feats:
            feat_ok += 1  # no grammatical morphs expected — lemma match alone is full credit
        else:
            def feat_hit(a: Analysis) -> bool:
                gs = {g for _, g in a}
                return expected_feats.issubset(gs)

            if any(feat_hit(a) for a in analyses):
                feat_ok += 1
            else:
                miss_feat.append(f"{w['surface']}={sorted(expected_feats)}")
    return {
        "tested": n,
        "parse_rate": round(parsed / n, 4) if n else 0.0,
        "lemma_recall": round(recalled / n, 4) if n else 0.0,
        "feature_recall": round(feat_ok / n, 4) if n else 0.0,
        "miss_parse": miss_parse[:12],
        "miss_lemma": miss_lemma[:10],
        "miss_feat": miss_feat[:12],
    }


def score_pair(model, wordforms: list[dict], lexicon: list[dict], *, sample: int = 400) -> dict:
    """Build the HC parse of `wordforms`' surfaces against `model` (an `engine.grammar.LangModel`,
    e.g. from `induce/tdd.py`'s output) and score. Requires the `hc` CLI — see `gold/hc_coverage.py
    ::hc_available()`. `wordforms`/`lexicon` come from `to_gold.rows_to_wordforms_and_lexicon`."""
    from engine.hc import run_parse

    # Same convention as `gold/goldio.py::load_gold`: a lemma's gloss is its lexicon entry's
    # first sense, keyed by `word` (the lemma's surface form).
    lemma_gloss = {e["word"]: e["senses"][0] for e in lexicon if e.get("senses")}
    wf = wordforms[:sample]
    surfaces = list({w["surface"] for w in wf})
    parses = run_parse(model, surfaces, chunk_size=25, chunk_timeout=25, templated=False)
    return score_parses(wf, lemma_gloss, parses)
