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
from golden.reference.hc_coverage import (  # noqa: E402
    _scripture_freqs, _slug, build_class_model, build_reference_model, hc_available)
from golden.reference.phonology_gold import active_phon_rules, phon_feats  # noqa: E402


def validate(pair: str, *, sample: int = 400, grammar: str = "lemma") -> dict:
    """Score the golden grammar against the wordform gold: does HC parse each scripture wordform, and to
    the RIGHT lemma? Lemma-recall = an HC analysis carries a morph glossed as the wordform's lemma (the
    model glosses each root with `_slug(lemma gloss)`, so the root-gloss identifies the lemma).

    grammar="lemma": lemmas-as-roots + UniMorph forms as allomorphs (memorised). grammar="class":
    induced stems + class affixes (generative — the rules drive parsing)."""
    gold = load_gold(pair)
    glosses = gold.get("glosses", {})
    freqs = _scripture_freqs(pair)
    model = build_class_model(pair) if grammar == "class" else build_reference_model(pair, n_roots=20000)
    pf = phon_feats(pair, model.charset)
    # the wordform gold whose lemma has a gloss (so the analysis is checkable), most frequent first
    wf = [w for w in gold.get("wordforms", []) if glosses.get(w["lemma"])]
    wf.sort(key=lambda x: -freqs.get(x["surface"], 0))
    wf = wf[:sample]
    surfaces = list({w["surface"] for w in wf})
    # class grammar restricts affixes by inflection class (encoded as POS) → parse pos-aware; any active
    # phonological rules for the pair are emitted into the grammar too.
    parses = run_parse(model, surfaces, chunk_size=25, chunk_timeout=25, templated=False,
                       phon_feats=pf, pos_aware=(grammar == "class"), phon_rules=active_phon_rules(pair))
    hc_loads = any(parses.get(s) for s in surfaces)
    from golden.reference.inflection import canon
    parsed = recalled = feat_ok = 0
    miss_parse: list[str] = []
    miss_lemma: list[str] = []
    miss_feat: list[str] = []
    for w in wf:
        analyses = parses.get(w["surface"]) or []
        if analyses:
            parsed += 1
        else:
            miss_parse.append(w["surface"])
            continue
        expect = _slug(glosses.get(w["lemma"]))            # the lemma's root-gloss in the grammar
        # a morph glosses the lemma if it equals the lemma gloss or starts "lemma|…" (irregular wholeform)
        def has_lemma(a):
            return any(g == expect or g.startswith(expect + "|") for _, g in a)
        if any(has_lemma(a) for a in analyses):
            recalled += 1
        else:
            miss_lemma.append(f"{w['surface']}→{w['lemma']}")
        # FEATURE recall: lemma + the right cell — via a feature-glossed affix (regular) OR the combined
        # "lemma|cell" gloss of an irregular wholeform (suppletion). Base = a bare-root analysis.
        cell = canon(w.get("features") or {})
        combined = f"{expect}|{cell}"
        def feat_hit(a):
            gs = [g for _, g in a]
            if cell == "BASE":          # no inflectional features to match → just need the right lemma
                return has_lemma(a)
            return (has_lemma(a) and cell in gs) or combined in gs
        if any(feat_hit(a) for a in analyses):
            feat_ok += 1
        else:
            miss_feat.append(f"{w['surface']}={cell[:20]}")
    n = len(wf)
    return {"pair": pair, "grammar": grammar, "hc_loads": hc_loads, "phon_features": len(pf), "tested": n,
            "roots": len(model.lexicon), "affixes": len(model.affixes),
            "parse_rate": round(parsed / n, 4) if n else 0.0,
            "lemma_recall": round(recalled / n, 4) if n else 0.0,
            "feature_recall": round(feat_ok / n, 4) if n else 0.0,
            "miss_parse": miss_parse[:12], "miss_lemma": miss_lemma[:10], "miss_feat": miss_feat[:12]}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--sample", type=int, default=400)
    ap.add_argument("--grammar", choices=["lemma", "class"], default="lemma",
                    help="lemma = forms-as-allomorphs (memorised); class = induced stems + class affixes (generative)")
    args = ap.parse_args(argv)
    if not hc_available():
        print("hc CLI not installed — skipping (this gate needs Hermit Crab).")
        return 0
    r = validate(args.pair, sample=args.sample, grammar=args.grammar)
    ok = "✓" if r["hc_loads"] else "✗ (grammar failed to load!)"
    print(f"[{args.pair}] {r['grammar']}-driven grammar — HC loads: {ok}   "
          f"{r['roots']} roots, {r['affixes']} affixes, {r['phon_features']} phon features   ({r['tested']} tested)")
    print(f"  parse rate:    {r['parse_rate']}  (HC produces some analysis)")
    print(f"  lemma recall:  {r['lemma_recall']}  (analysis carries the RIGHT lemma)")
    print(f"  feature recall:{r['feature_recall']}  (analysis carries lemma + the RIGHT features — full completeness)")
    if r["miss_feat"]:
        print(f"  !features: {', '.join(r['miss_feat'])}")
    if r["miss_parse"]:
        print(f"  no parse:  {', '.join(r['miss_parse'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
