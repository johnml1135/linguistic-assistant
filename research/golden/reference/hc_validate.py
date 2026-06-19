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

from golden.grammar import LexEntry  # noqa: E402
from golden.hc import run_parse  # noqa: E402

from golden.reference.compile import PAIR_DIR  # noqa: E402
from golden.reference.goldio import load_gold  # noqa: E402
from golden.reference.hc_coverage import _scripture_freqs, _slug, build_reference_model, hc_available  # noqa: E402
from golden.reference.phonology_gold import phon_feats  # noqa: E402


def validate(pair: str, *, sample: int = 400, close: bool = False) -> dict:
    model = build_reference_model(pair)
    gold = load_gold(pair)
    glosses, pos = gold.get("glosses", {}), gold.get("pos", {})
    known = set(glosses) | set(gold.get("lemmas", [])) | set(pos)
    freqs = _scripture_freqs(pair)
    # golden entries = attested words the references know (not bare proper nouns), most frequent first
    entries = sorted((w for w in gold.get("in_scripture", [])
                      if w in known and w.isalpha() and len(w) >= 2), key=lambda w: -freqs.get(w, 0))[:sample]
    pf = phon_feats(pair, model.charset)
    parses = run_parse(model, entries, chunk_size=25, chunk_timeout=25, templated=False, phon_feats=pf)
    hc_loads = any(parses.get(w) for w in entries)  # a failed grammar load → nothing parses at all
    parsed = [w for w in entries if parses.get(w)]
    residual = [w for w in entries if not parses.get(w)]

    closed = None
    if close and residual:
        # lexicalise the residual: each is a real word with a reference gloss → add as its own root.
        extra = [LexEntry(form=w, gloss=_slug(glosses.get(w) or "?"), pos=(pos.get(w) or "Noun")) for w in residual]
        model.lexicon.extend(extra)
        pf2 = phon_feats(pair, model.charset)
        parses2 = run_parse(model, residual, chunk_size=25, chunk_timeout=25, templated=False, phon_feats=pf2)
        still = [w for w in residual if not parses2.get(w)]
        closed = {"lexicalised": len(extra), "still_unparsed": still[:15],
                  "rate_after": round((len(parsed) + (len(residual) - len(still))) / len(entries), 4) if entries else 0.0}

    rate = round(len(parsed) / len(entries), 4) if entries else 0.0
    return {"pair": pair, "hc_loads": hc_loads, "phon_features": len(pf),
            "golden_entries_tested": len(entries), "parsed": len(parsed), "compositional_rate": rate,
            "residual": len(residual), "residual_sample": residual[:15], "closed": closed}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--sample", type=int, default=400)
    ap.add_argument("--close", action="store_true", help="lexicalise the residual to reach 100% on the golden set")
    args = ap.parse_args(argv)
    if not hc_available():
        print("hc CLI not installed — skipping (this gate needs Hermit Crab).")
        return 0
    r = validate(args.pair, sample=args.sample, close=args.close)
    ok = "✓" if r["hc_loads"] else "✗ (grammar failed to load!)"
    print(f"[{args.pair}] HC loads the golden grammar: {ok}   phonological features active: {r['phon_features']}")
    print(f"  compositional parse of golden entries: {r['compositional_rate']} "
          f"({r['parsed']}/{r['golden_entries_tested']}; {r['residual']} residual)")
    if r["residual_sample"]:
        print(f"  residual (irregular/uncovered): {', '.join(r['residual_sample'])}")
    if r["closed"]:
        print(f"  after lexicalising the residual: {r['closed']['rate_after']} "
              f"(+{r['closed']['lexicalised']} roots; {len(r['closed']['still_unparsed'])} still unparsed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
