"""CLI: compute the grammar-assessment scorecard.

    # structural scorecard from a FieldWorks/LibLCM dump or a LIFT export (no parser needed)
    python research/assess/assess.py --source liblcm --path project.fwdata
    python research/assess/assess.py --source lift   --path lexicon.lift

    # full scorecard (parse-based + structural) over a golden HermitCrab grammar — needs the hc CLI
    python research/assess/assess.py --source hermitcrab --lang lez

    # offline demo — full hermitcrab scorecard + worst-part ranking via a fake parser (no hc, no network)
    python research/assess/assess.py --source demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RESEARCH))

from assess.builders import assess_hermitcrab, assess_liblcm, assess_lift  # noqa: E402
from assess.worst_part import worst_part_ranking  # noqa: E402


def _demo() -> int:
    """A tiny concatenative LangModel + a fake parser, so the whole path runs with no hc/network."""
    from engine.grammar import Affix, LangModel, LexEntry

    model = LangModel(
        code="demo",
        lexicon=[LexEntry("kufamba", "walk", count=14), LexEntry("toto", "child", count=9),
                 LexEntry("ghost", "unused", count=0)],
        affixes=[Affix("ni", "1SG", "prefix", count=20), Affix("ka", "PST", "prefix", count=3)],
    )
    # gold decompositions (underlying form -> [(morph_form, gloss)]) → gloss lines
    gold_decomp = {
        "nikufamba": [("ni", "1SG"), ("kufamba", "walk")],
        "kakufamba": [("ka", "PST"), ("kufamba", "walk")],
        "nitoto": [("ni", "1SG"), ("toto", "child")],
    }
    gold = {w: tuple(g for _, g in d) for w, d in gold_decomp.items()}

    def fake_parse(m, words):
        forms = {e.form for e in m.lexicon} | {a.form for a in m.affixes}
        out = {}
        for w in words:
            d = gold_decomp.get(w, [])
            out[w] = [tuple(g for _, g in d)] if d and all(f in forms for f, _ in d) else []
        return out

    sc = assess_hermitcrab(model, list(gold), gold=gold, grammar_id="demo", parse_fn=fake_parse)
    print(sc.to_json())
    print("\nworst parts (highest worstness first):")
    for r in worst_part_ranking(model, gold, parse_fn=fake_parse):
        print(f"  {r['worstness']:+.3f}  {r['kind']:5} {r['form']}/{r['gloss']}  "
              f"(benefit={r['benefit']}, cost={r['cost']})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, choices=["liblcm", "lift", "hermitcrab", "demo"])
    ap.add_argument("--path", help="path to the .fwdata/LibLCM dump or .lift file")
    ap.add_argument("--lang", help="golden language code (hermitcrab source)")
    args = ap.parse_args()

    if args.source == "demo":
        return _demo()
    if args.source in ("liblcm", "lift"):
        if not args.path:
            ap.error("--path is required for liblcm/lift")
        text = Path(args.path).read_text(encoding="utf-8")
        sc = assess_liblcm(text, grammar_id=args.path) if args.source == "liblcm" \
            else assess_lift(text, grammar_id=args.path)
        print(sc.to_json())
        return 0
    # hermitcrab: load a golden language model + corpus + gold, then assess via the hc CLI.
    if not args.lang:
        ap.error("--lang is required for the hermitcrab source")
    try:
        from engine.build import load_assessment_inputs  # type: ignore
    except Exception:
        print("[assess] golden build loader not available here. Use --source demo for an offline run, "
              "or wire load_assessment_inputs(lang) -> (LangModel, corpus_words, gold) to the golden build.")
        return 1
    model, corpus_words, gold = load_assessment_inputs(args.lang)  # type: ignore
    sc = assess_hermitcrab(model, corpus_words, gold=gold, grammar_id=args.lang)
    print(sc.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
