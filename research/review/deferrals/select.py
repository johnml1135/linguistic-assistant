"""Stage 2 — candidate selection: pick the next-most-resolvable thing to attack (deterministic, no LLM).

Two complementary selections:
  * `rank_targets` — over the currently failing/deferred forms, rank by **impact** (corpus frequency ×
    related wordforms) × **resolvability** (closeness to a known lemma/affix). Cheap (no HC).
  * `suspect_constructs` — over the EXISTING grammar, the worst-part ablation ranking
    (`research/assess/worst_part`): the construct whose removal most improves the grammar is the prime
    target to repair/narrow (D9/D14). Bounded to a gold sample so it stays feasible.

`cluster_forms` groups distinct surface forms that align to the same translation word and share a stem
into a single candidate ("these forms are likely one lexeme/paradigm").
"""

from __future__ import annotations

from collections import defaultdict

from gold.goldio import load_gold

from . import counterfactual as CF
from .taxonomy import _known_affix_split, _nearest_lemma


def resolvability(word: str, gold: dict) -> float:
    """[0,1] — how close `word` is to something the grammar already knows (a likely-cheap fix).

    A shared prefix with a known lemma, or a clean strip to a known stem via a known affix, scores high;
    an isolated unfamiliar form scores low (it needs a fresh root — more elicitation)."""
    word = word.lower()
    lemmas = gold.get("lemmas", [])
    near = _nearest_lemma(word, lemmas)
    score = 0.0
    if near:
        shared = sum(1 for a, b in zip(word, near) if a == b)
        score = max(score, min(1.0, shared / max(len(word), 1) + 0.2))
    split = _known_affix_split(word, gold.get("affixes", []))
    if split and split[0] in set(lemmas):
        score = max(score, 0.9)              # stem+known-affix where the stem is a known lemma → very cheap
    elif split:
        score = max(score, 0.6)
    return round(score, 3)


def grammar_state(pair: str, *, base=None, pf=None, sample: int = 120) -> str:
    """The parsing maturity of the grammar (task 14.2): 'cold' (little parses → bootstrap lexemes),
    'mid' (affix/class work), or 'mature' (irregulars/phonology/edge cases). Drives stage-2 weighting."""
    from engine.hc import run_parse
    from .counterfactual import load_base
    if base is None or pf is None:
        base, pf = load_base(pair)
    freqs = CF._freqs(pair)
    words = [w for w, _ in freqs.most_common() if w.isalpha() and len(w) >= 2][:sample]
    parses = run_parse(base, words, templated=False, phon_feats=pf, chunk_timeout=CF.CHUNK_TIMEOUT)
    cov = sum(1 for w in words if parses.get(w)) / len(words) if words else 0.0
    return "cold" if cov < 0.4 else "mid" if cov < 0.8 else "mature"


def rank_targets(pair: str, words: list[str], *, gold: dict | None = None, state: str | None = None) -> list[dict]:
    """Rank failing/deferred targets: high-impact AND resolvable first. Deterministic, HC-free.

    `state` (cold|mid|mature) tilts the weighting (task 14.2): a cold grammar favours frequent lexeme
    bootstrapping (impact-weighted); a mature one favours the resolvable tail (resolvability-weighted)."""
    gold = gold or load_gold(pair)
    freqs = CF._freqs(pair)
    res_w = {"cold": 0.3, "mid": 0.5, "mature": 0.8}.get(state or "mid", 0.5)
    rows = []
    for w in dict.fromkeys(w.lower() for w in words):
        rel = [x for x in freqs if CF._shares_stem(w, x)]
        impact = sum(freqs.get(x, 0) for x in rel)
        res = resolvability(w, gold)
        rows.append({"word": w, "freq": freqs.get(w, 0), "impact": impact, "resolvability": res,
                     "score": round(impact * (1.0 - res_w + res_w * res), 2)})
    rows.sort(key=lambda r: (-r["score"], -r["freq"], r["word"]))
    return rows


def cluster_forms(pair: str, words: list[str], *, en_of: dict | None = None) -> list[dict]:
    """Group distinct surface forms that (a) align to the same translation word and (b) share a stem,
    into one candidate ('likely one lexeme/paradigm'). `en_of` maps surface→pivot word (e.g. the
    aligner's top-1); without it, clustering falls back to shared-stem only."""
    en_of = en_of or {}
    words = [w.lower() for w in dict.fromkeys(words)]
    clusters: list[dict] = []
    used: set[str] = set()
    for i, w in enumerate(words):
        if w in used:
            continue
        group = [w]
        for x in words[i + 1:]:
            if x in used:
                continue
            same_en = en_of.get(w) and en_of.get(w) == en_of.get(x)
            if (same_en or not en_of) and CF._shares_stem(w, x):
                group.append(x)
                used.add(x)
        used.add(w)
        if len(group) > 1:
            stem_len = min(len(a) for a in group)
            while stem_len > 0 and len({a[:stem_len] for a in group}) > 1:
                stem_len -= 1
            clusters.append({"forms": sorted(group), "shared_stem": group[0][:stem_len],
                             "pivot": en_of.get(w, "")})
    return clusters


def suspect_constructs(pair: str, *, sample: int = 60, top: int = 10) -> list[dict]:
    """The worst-part ablation ranking over a bounded gold sample — the existing constructs most worth
    repairing/narrowing (also the prime suspects for a wrong rule). Reuses research/assess/worst_part.

    Bounded: a leave-one-out re-parse per construct is expensive, so we run it on the most frequent
    constructs against a small gold word sample. Requires HC."""
    from assess.worst_part import worst_part_ranking

    from .counterfactual import load_base

    base, pf = load_base(pair)
    gold = load_gold(pair)
    # a small gold {word: gloss_line} sample from the wordforms (frequency-ordered, bounded)
    freqs = CF._freqs(pair)
    wf = sorted(gold.get("wordforms", []), key=lambda w: -freqs.get(w["surface"].lower(), 0))
    gold_lines: dict = {}
    for w in wf[:sample]:
        surface = w["surface"].lower()
        # a coarse gold gloss line: lemma gloss (the reliable identity); good enough to rank worstness
        gloss = (gold.get("glosses", {}).get(w["lemma"]) or w["lemma"])
        gold_lines[surface] = (gloss,)
    # bound the construct set to the most frequent (keep the leave-one-out feasible)
    from engine.grammar import LangModel
    small = LangModel(code=base.code,
                      lexicon=sorted(base.lexicon, key=lambda e: -e.count)[:sample],
                      affixes=base.affixes)

    def parse_fn(model, words):
        from engine.hc import gloss_seq, run_parse
        raw = run_parse(model, words, templated=False, phon_feats=pf, chunk_timeout=CF.CHUNK_TIMEOUT)
        return {x: list(dict.fromkeys(gloss_seq(a) for a in raw.get(x, []))) for x in words}

    ranking = worst_part_ranking(small, gold_lines, parse_fn=parse_fn)
    return ranking[:top]
