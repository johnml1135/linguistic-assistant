"""Freeze a certified golden set for one language and write all five artifacts.

Usage::

    python -m golden.build --lang lez \\
        --igt golden/_sources/2023glossingST/data_v1/Lezgi/lez-train-track2-uncovered \\
        --license CC-BY-NC-4.0 --out golden/lez

Writes ``raw/igt.jsonl``, ``gold/lexicon.lift``, ``gold/grammar.hcgr.xml``,
``gold/analyses.jsonl`` and ``meta.json`` (with the HC round-trip coverage that certifies
the grammar). No human in the loop — the round-trip number is the certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from . import hc, igt
from .grammar import build_model


def freeze(lang: str, igt_path: str, out_dir: str, license: str, timeout: int = 900,
           min_affix_count: int = 1) -> dict:
    records = igt.parse_file(igt_path)
    words = list(igt.iter_words(records))
    model = build_model(lang, words, min_affix_count=min_affix_count)

    # Distinct underlying wordforms + their gold analyses.
    gold, seen = [], set()
    for w in words:
        if w.underlying in seen:
            continue
        seen.add(w.underlying)
        gold.append((w.underlying, w.gold_analysis))

    rt = hc.round_trip(model, gold, timeout=timeout)

    out = Path(out_dir)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "gold").mkdir(parents=True, exist_ok=True)

    # raw/: what a linguist (or the agent) would analyse — surface + translation only.
    # Field names match proposal.contract.IGTRecord / research/eval loader (text/translation);
    # gloss + segmentation are withheld (they are the oracle).
    with (out / "raw" / "igt.jsonl").open("w", encoding="utf-8") as f:
        for i, r in enumerate(records):
            f.write(json.dumps({"id": str(i), "text": r.surface, "translation": r.translation},
                               ensure_ascii=False) + "\n")

    # gold/: lexicon (LIFT), morphology (HC grammar), per-word gold analyses.
    from .lift_emit import build_lift
    (out / "gold" / "lexicon.lift").write_text(build_lift(model), encoding="utf-8")
    (out / "gold" / "grammar.hcgr.xml").write_text(hc.build_grammar_xml(model), encoding="utf-8")
    with (out / "gold" / "analyses.jsonl").open("w", encoding="utf-8") as f:
        for u, analysis in gold:
            f.write(json.dumps({"form": u, "analysis": analysis}, ensure_ascii=False) + "\n")

    grammar_hash = hashlib.sha256(
        (out / "gold" / "grammar.hcgr.xml").read_bytes()
    ).hexdigest()[:16]

    meta = {
        "language": lang,
        "source": Path(igt_path).name,
        "license": license,
        "license_note": "NonCommercial: research-use gold; pipeline is the reusable asset.",
        "counts": {**model.summary(), "records": len(records),
                   "distinct_wordforms": len(gold)},
        "grammar_model": {
            "morphotactics": "affix-template (position-class slots, one filler/slot, ordered)",
            "multi_slot": True,  # MoInflAffMsa.Slots is a sequence: affixes fill all attested slots
            "min_affix_count": min_affix_count,
            "best_practice_refs": ["linguistics/primitives/affix-template-and-slot.md",
                                   "linguistics/primitives/morphosyntactic-analysis.md"],
        },
        "certification": {"method": "hermitcrab-gloss-round-trip", **rt.as_dict()},
        "grammar_sha256_16": grammar_hash,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--igt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--license", default="CC-BY-NC-4.0")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--min-affix-count", type=int, default=1,
                    help="prune affixes seen fewer than N times (tractability for high-affix langs)")
    a = ap.parse_args()
    meta = freeze(a.lang, a.igt, a.out, a.license, a.timeout, a.min_affix_count)
    print(json.dumps(meta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
