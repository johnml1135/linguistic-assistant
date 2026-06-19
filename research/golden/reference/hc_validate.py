"""Is HC happy with the golden set? Build the grammar from the gold (roots + allomorphs + grammar_rules
+ the phonological feature substrate) and check Hermit Crab (1) LOADS it without error and (2) parses the
golden entries.

"The golden set" here = scripture-attested words the references actually know as words (have a gloss, a
lemma, or a POS) — i.e. excluding bare proper nouns, which are named entities, not morphology. We report
the compositional parse rate over those, and with `--close` we LEXICALISE the residual (add each still-
unparsed known word as its own LexEntry, which is legitimate — it is a real word with a gloss) to show the
golden set can be made 100% HC-parseable. Run: `python golden/reference/hc_validate.py --pair spa`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from golden.hc import run_parse  # noqa: E402

from golden.reference.compile import PAIR_DIR  # noqa: E402
from golden.reference.goldio import load_gold  # noqa: E402
from golden.reference.hc_coverage import _scripture_freqs, _slug, build_reference_model, hc_available  # noqa: E402
from golden.reference.phonology_gold import phon_feats  # noqa: E402


def validate(pair: str, *, sample: int = 400) -> dict:
    """Score the golden grammar against the wordform gold: does HC parse each scripture wordform, and to
    the RIGHT lemma? Lemma-recall = an HC analysis carries a morph glossed as the wordform's lemma (the
    model glosses each root with `_slug(lemma gloss)`, so the root-gloss identifies the lemma)."""
    gold = load_gold(pair)
    glosses = gold.get("glosses", {})
    freqs = _scripture_freqs(pair)
    model = build_reference_model(pair, n_roots=20000)  # all biblical lemmas as roots, so recall is fair
    pf = phon_feats(pair, model.charset)
    # the wordform gold whose lemma has a gloss (so the analysis is checkable), most frequent first
    wf = [w for w in gold.get("wordforms", []) if glosses.get(w["lemma"])]
    wf.sort(key=lambda x: -freqs.get(x["surface"], 0))
    wf = wf[:sample]
    surfaces = list({w["surface"] for w in wf})
    parses = run_parse(model, surfaces, chunk_size=25, chunk_timeout=25, templated=False, phon_feats=pf)
    hc_loads = any(parses.get(s) for s in surfaces)
    parsed = recalled = 0
    miss_parse: list[str] = []
    miss_lemma: list[str] = []
    for w in wf:
        analyses = parses.get(w["surface"]) or []
        if analyses:
            parsed += 1
        else:
            miss_parse.append(w["surface"])
            continue
        expect = _slug(glosses.get(w["lemma"]))            # the lemma's root-gloss in the grammar
        if any(expect in [g for _, g in a] for a in analyses):
            recalled += 1
        else:
            miss_lemma.append(f"{w['surface']}→{w['lemma']}")
    n = len(wf)
    return {"pair": pair, "hc_loads": hc_loads, "phon_features": len(pf), "tested": n,
            "parse_rate": round(parsed / n, 4) if n else 0.0,
            "lemma_recall": round(recalled / n, 4) if n else 0.0,
            "miss_parse": miss_parse[:12], "miss_lemma": miss_lemma[:12]}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--sample", type=int, default=400)
    args = ap.parse_args(argv)
    if not hc_available():
        print("hc CLI not installed — skipping (this gate needs Hermit Crab).")
        return 0
    r = validate(args.pair, sample=args.sample)
    ok = "✓" if r["hc_loads"] else "✗ (grammar failed to load!)"
    print(f"[{args.pair}] HC loads golden grammar: {ok}   phon features active: {r['phon_features']}   "
          f"({r['tested']} wordforms tested)")
    print(f"  parse rate:   {r['parse_rate']}  (HC produces some analysis)")
    print(f"  lemma recall: {r['lemma_recall']}  (analysis carries the RIGHT lemma — the real gate)")
    if r["miss_lemma"]:
        print(f"  wrong/!lemma: {', '.join(r['miss_lemma'])}")
    if r["miss_parse"]:
        print(f"  no parse:     {', '.join(r['miss_parse'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
