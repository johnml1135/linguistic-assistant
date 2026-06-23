"""How FULL is the golden set? — a per-language × {lexicography, morphology, phonology} scorecard.

The goal is the fullest possible golden set for the four NTs. This measures fullness on every axis so the
work targets the real gaps (not guesses): lexicography (lemmas + glosses + validated source), morphology
(inflection classes + wordform analyses + affixes), phonology (inventory + rules). Reads the frozen files
only — cheap, no HC/Gemma. Run: `python golden/reference/completeness.py`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from gold.compile import PAIR_DIR  # noqa: E402

FROZEN = _THIS.parents[1] / "golden_sets"


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line] if p.exists() else []


def score(pair: str) -> dict:
    d = FROZEN / pair
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8")) if (d / "meta.json").exists() else {}
    stats = meta.get("stats", {})
    lex = _jsonl(d / "lexicon.jsonl")
    wf = _jsonl(d / "wordforms.jsonl")
    classes = _jsonl(d / "inflection_classes.jsonl")
    phon = _jsonl(d / "phonology.jsonl")
    phon_derived = _jsonl(d / "phonology_induced.jsonl")   # corpus-derived, data-validated rules
    rules = _jsonl(d / "grammar_rules.jsonl")
    seg = _jsonl(d / "segmentation.jsonl")

    glossed = [e for e in lex if e.get("senses")]
    src = Counter(e.get("gloss_source", "wiktionary") for e in glossed)
    classed = [e for e in lex if e.get("inflection_class")]
    phon_rules = [r for r in phon if r.get("type") == "rule"]
    return {
        "pair": pair,
        "lexicography": {
            "lemmas": len(lex), "glossed": len(glossed),
            "gloss_pct": round(100 * len(glossed) / len(lex)) if lex else 0,
            "sources": dict(src), "homographs": sum(1 for e in lex if e.get("homograph")),
            "key_terms": stats.get("key_terms", 0)},
        "morphology": {
            # fusional langs (spa/ind) → inflection classes; agglutinative (tgl/swh) → segmentation + affixes
            "inflection_classes": len(classes), "lemmas_classed": len(classed), "wordforms": len(wf),
            "affixes_gold": len(rules), "segmented_words": len(seg),
            "distinct_affixes": len({a for s in seg for a in (s.get("prefixes", []) + s.get("suffixes", []))})},
        "phonology": {
            "segments": sum(1 for r in phon if r.get("type") == "segment"),
            "natural_classes": sum(1 for r in phon if r.get("type") == "natural_class"),
            "rules_total": len(phon_rules) + len(phon_derived),
            "rules_active": sum(1 for r in phon_rules if r.get("status") == "active"),
            "rules_derived": len(phon_derived),                     # corpus-validated (data-derived)
            "rules_staged": sum(1 for r in phon_rules if r.get("status") == "staged")},
        "scripture_coverage": stats.get("scripture_coverage", 0.0),
    }


def main(argv: list[str] | None = None) -> int:
    rows = [score(p) for p in PAIR_DIR]
    print("GOLDEN-SET COMPLETENESS — 4 languages × {lexicography, morphology, phonology}\n")
    print(f"{'':6} {'lemmas':>7} {'gloss%':>7} {'classes':>8} {'segmwords':>10} {'affixes':>8} {'phonR':>7} {'NTcov':>7}")
    for r in rows:
        lx, mo, ph = r["lexicography"], r["morphology"], r["phonology"]
        morph = mo["inflection_classes"] or "—"
        ph_cell = f"{ph['rules_active']}a+{ph.get('rules_derived', 0)}d/{ph['rules_total']}"
        print(f"{r['pair']:6} {lx['lemmas']:>7} {lx['gloss_pct']:>6}% {str(morph):>8} {mo['segmented_words']:>10} "
              f"{mo['distinct_affixes']:>8} {ph_cell:>9} {r['scripture_coverage']:>7}")
    print("\nMorphology model: spa/ind = inflection classes (fusional); tgl/swh = segmentation + affixes (agglutinative)")
    print("GAPS (what 'full' still needs):")
    for r in rows:
        g = []
        mo = r["morphology"]
        if mo["inflection_classes"] < 3 and mo["segmented_words"] == 0:
            g.append("no morphology yet (run segment.py)")
        if mo["distinct_affixes"] and not False:
            pass
        if r["phonology"]["rules_active"] == 0 and r["phonology"].get("rules_derived", 0) == 0:
            g.append("no phonological rules (0 active, 0 derived)")
        if r["lexicography"]["gloss_pct"] < 80:
            g.append(f"gloss {r['lexicography']['gloss_pct']}% (<80) — Gemma --target needy --apply")
        affix_labeled = "affixes need Gemma functions (propose.py --mode morph)" if mo["segmented_words"] else ""
        print(f"  {r['pair']}: {'; '.join(g) if g else 'lexicography+morphology solid'}{'; ' + affix_labeled if affix_labeled and mo['inflection_classes']<3 else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
