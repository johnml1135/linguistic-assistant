"""Score the induced grammar/lexicon against the compiled reference gold — in LibLCM terms.

Reads `golden_set.json` (from compile.py) + `golden_lexicon.txt` and the cycle's `out/<pair>_model.json`:
  * **POS accuracy** — the root's POS, mapped to a LibLCM `PartOfSpeech`, vs the gold (3-way-voted) POS.
  * **Gloss accuracy** — the root's English gloss vs the Wiktionary bilingual gloss (token overlap).
  * **Lexicon validity** — fraction of induced roots that are real words (in the gold lexicon).
  * **Gloss validity** — fraction of glosses that are unfoldingWord biblical key terms.

Run: `python golden/reference/evaluate.py --pair spa`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

import liblcm  # noqa: E402
from golden.reference.goldio import load_gold  # noqa: E402

FROZEN = _THIS.parents[2] / "golden_sets"            # the frozen evaluation target (committed)
OUT = _THIS.parents[2] / "cycle" / "out"             # the hill-climber's working copy (regenerable)


def evaluate(pair: str) -> dict:
    gold = load_gold(pair)
    model = json.loads((OUT / f"{pair}_model.json").read_text(encoding="utf-8"))
    roots = model["roots"]
    gold_pos: dict[str, str] = gold.get("pos", {})           # LibLCM PartOfSpeech
    gold_gloss: dict[str, str] = gold.get("glosses", {})     # bilingual (Wiktionary)
    lexicon = set(gold.get("lexicon", []))
    key = set(gold.get("key_terms", []))
    report: dict = {"pair": pair, "sources": gold.get("sources", []), "roots": len(roots)}

    # 1) POS accuracy in LibLCM terms
    pchecked = pcorrect = 0
    for r in roots:
        g = gold_pos.get(r["form"].lower())
        if g:
            pchecked += 1
            if liblcm.pos_from_cycle(r.get("pos", "")) == g:
                pcorrect += 1
    if pchecked:
        report["pos"] = {"checked": pchecked, "correct": pcorrect, "accuracy": round(pcorrect / pchecked, 4)}

    # 2) bilingual gloss accuracy (cycle gloss token appears in the Wiktionary sense gloss)
    gchecked = gcorrect = 0
    for r in roots:
        cg = (r.get("gloss") or "").lower().strip()
        ref = gold_gloss.get(r["form"].lower())
        if cg and cg != "?" and ref:
            gchecked += 1
            if cg in {t.strip(".,;:()") for t in ref.lower().split()} or cg in ref.lower():
                gcorrect += 1
    if gchecked:
        report["gloss_accuracy"] = {"checked": gchecked, "correct": gcorrect,
                                    "accuracy": round(gcorrect / gchecked, 4)}

    # 3) lexicon validity
    if lexicon:
        hits = sum(1 for r in roots if r["form"].lower() in lexicon)
        report["lexicon_validity"] = {"roots_in_reference": hits,
                                      "frac": round(hits / len(roots), 4) if roots else 0.0}

    # 4) gloss validity vs unfoldingWord key terms
    if key:
        glosses = {r["gloss"].lower() for r in roots if r.get("gloss") and r["gloss"] != "?"}
        overlap = sorted(glosses & key)
        report["gloss_validity"] = {"glosses": len(glosses), "are_key_terms": len(overlap),
                                    "examples": overlap[:12]}

    # the eval RESULT scores the working copy against the gold → it is working output, not gold.
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{pair}_refeval.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True)
    args = ap.parse_args(argv)
    r = evaluate(args.pair)
    print(f"[{args.pair}] reference eval (sources {r['sources']}):")
    if "pos" in r:
        print(f"  POS accuracy (LibLCM): {r['pos']['accuracy']} ({r['pos']['correct']}/{r['pos']['checked']})")
    if "gloss_accuracy" in r:
        print(f"  gloss accuracy (Wikt): {r['gloss_accuracy']['accuracy']} "
              f"({r['gloss_accuracy']['correct']}/{r['gloss_accuracy']['checked']})")
    if "lexicon_validity" in r:
        print(f"  lexicon validity:      {r['lexicon_validity']['frac']} "
              f"({r['lexicon_validity']['roots_in_reference']}/{r['roots']})")
    if "gloss_validity" in r:
        g = r["gloss_validity"]
        print(f"  gloss validity:        {g['are_key_terms']}/{g['glosses']} are key terms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
