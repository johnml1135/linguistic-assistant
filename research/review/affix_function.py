"""Affix FUNCTION induction — give each affix its grammatical meaning, the system's documented blind spot.

The coverage loop SEGMENTS words but can't say what the affixes DO: THOT word-alignment structurally
misses functional morphemes (a tense/number/person marker never translates to an English WORD), so the
morph-align accept gate defers every functional affix and the gold-less languages get no affix functions
at all. But a functional morpheme correlates with a grammatical FEATURE — exactly what the English pivot's
UD morphology exposes (Number, Person, Tense, Case, Definite, Polarity, …). This module generalises
`project.label_tam` (which already does this for Tense on verbs) to EVERY feature: project the English
features onto each vernacular word, and find, for each affix, the feature value it predicts above chance.

The verdict is graded by HELD-OUT PREDICTION, not opinion: learn affix→feature on a train split, then
measure how often the affix predicts that feature on unseen verses. That accuracy is the confidence a
human / Opus reviewer reviews — and the metric the dimension never had.

CLI:  python -m review.affix_function --pair swh [--present]
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

LIFT_MIN = 1.6          # min P(feat|affix)/P(feat) — the affix must raise the feature above its base rate
MIN_SUPPORT = 6         # min affix+feature co-occurrences
MIN_SHARE = 0.30        # min fraction of the affix's tokens that carry the feature value
# inflectional UD features worth labelling an affix with (skip lexical/POS-ish ones)
FEATURE_KEYS = {"Number", "Person", "Tense", "Aspect", "Mood", "Case", "Definite", "Polarity",
                "Gender", "VerbForm", "Degree", "PronType", "Voice", "NumType"}


def _bears(word: str, form: str, kind: str) -> bool:
    if len(word) <= len(form) + 1:
        return False
    return word.startswith(form) if kind == "prefix" else word.endswith(form)


def cooccur(rows: list[tuple[str, dict]], affixes: list[tuple[str, str]]):
    """Pure core: rows = [(vernacular_word, english_feats)], affixes = [(form, kind)]. Tally affix↔
    (feature=value) co-occurrence + base rates. Returns (per_affix Counter of fv, affix_token_counts,
    base Counter of fv, total)."""
    per: dict[str, Counter] = defaultdict(Counter)
    n_aff: Counter = Counter()
    base: Counter = Counter()
    total = 0
    for word, feats in rows:
        fvs = [f"{k}={v}" for k, v in feats.items() if k in FEATURE_KEYS]
        if fvs:
            total += 1
            for fv in fvs:
                base[fv] += 1
        for form, kind in affixes:
            if _bears(word, form, kind):
                n_aff[(form, kind)] += 1
                for fv in fvs:
                    per[(form, kind)][fv] += 1
    return per, n_aff, base, total


def rank_functions(per, n_aff, base, total, *, lift_min=LIFT_MIN, min_support=MIN_SUPPORT,
                   min_share=MIN_SHARE) -> dict:
    """For each affix, the feature value it predicts above chance (by lift), gated on support + share."""
    out = {}
    for aff, c in per.items():
        na = n_aff[aff]
        if na < min_support:
            continue
        best = None
        for fv, n in c.items():
            share = n / na
            base_rate = base[fv] / total if total else 0
            lift = (share / base_rate) if base_rate else 0.0
            if n >= min_support and share >= min_share and lift >= lift_min:
                cand = {"function": fv, "support": n, "share": round(share, 3), "lift": round(lift, 2)}
                if best is None or (cand["lift"], cand["support"]) > (best["lift"], best["support"]):
                    best = cand
        if best:
            out[aff] = best
    return out


def _project_rows(pair: str, pivot: str, sample: int) -> list[tuple[str, dict]]:
    from review.project import get_parser, _word_alignment, project_verse
    parser = get_parser(pivot)
    if parser is None:
        return []
    verses, table = _word_alignment(pair, sample)
    rows = []
    for _ref, src, tgt in verses:
        if not src or not tgt:
            continue
        for p in project_verse(parser(" ".join(src)), src, tgt, table):
            rows.append((p["vern"], p.get("feats", {}) or {}))
    return rows


def _affixes(pair: str) -> list[tuple[str, str]]:
    from induce.tdd import _load_prior_model
    m = _load_prior_model(pair)
    if not m:
        return []
    return [(a.form, a.kind) for a in m.affixes if a.kind in ("prefix", "suffix") and len(a.form) >= 1]


def induce_affix_functions(pair: str, *, pivot: str = "en", sample: int = 0, holdout: float = 0.3) -> dict:
    """Project English features, learn affix→function on a TRAIN split, and validate by HELD-OUT prediction
    (does the affix predict its learned feature on unseen verses?). Returns per-affix function + the
    held-out accuracy that grades it."""
    rows = _project_rows(pair, pivot, sample)
    affixes = _affixes(pair)
    if not rows or not affixes:
        return {"pair": pair, "error": "no projection rows or no affixes", "functions": {}}
    cut = int(len(rows) * (1 - holdout))
    train, test = rows[:cut], rows[cut:]
    learned = rank_functions(*cooccur(train, affixes))
    # held-out: of the test words bearing the affix, how often is the learned feature value present?
    val: dict = {}
    for aff, info in learned.items():
        form, kind = aff
        fv = info["function"]
        hit = seen = 0
        for word, feats in test:
            if _bears(word, form, kind):
                seen += 1
                if fv in [f"{k}={v}" for k, v in feats.items()]:
                    hit += 1
        info = dict(info)
        info["heldout_n"] = seen
        info["heldout_accuracy"] = round(hit / seen, 3) if seen else None
        val[f"{form}({kind})"] = info
    ranked = dict(sorted(val.items(), key=lambda kv: -(kv[1]["lift"])))
    return {"pair": pair, "n_rows": len(rows), "n_affixes": len(affixes),
            "n_labelled": len(ranked), "functions": ranked}


def present(pair: str, **kw) -> dict:
    r = induce_affix_functions(pair, **kw)
    if r.get("error"):
        print(f"{pair}: {r['error']}")
        return r
    print(f"\n=== {pair}: affix functions ({r['n_labelled']}/{r['n_affixes']} affixes labelled, "
          f"{r['n_rows']} projected words) ===")
    print(f"{'affix':12} {'function':18} {'support':>7} {'share':>6} {'lift':>5} {'heldout':>8}")
    for aff, info in r["functions"].items():
        acc = info["heldout_accuracy"]
        print(f"{aff:12} {info['function']:18} {info['support']:7} {info['share']:6} {info['lift']:5} "
              f"{(str(acc) + ' (n=' + str(info['heldout_n']) + ')') if acc is not None else 'n/a':>8}")
    return r


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Induce affix grammatical functions from projected features.")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--sample", type=int, default=0)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    present(a.pair, sample=a.sample)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
