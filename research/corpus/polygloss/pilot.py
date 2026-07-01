"""Run one PolyGloss pilot language end to end: build -> induce (HC-gated) -> score against the
held-out hand-annotated gold. Ties together `build.py`, `induce/tdd.py` (via the §4.3 impersonate-a-
pair adapter), and `score.py`. See Polygloss_integration.md §6 steps 3-4.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from .build import build_pilot, pair_key, register_pair  # noqa: E402
from .score import score_pair  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "out"

# Keys `build_pilot` adds for in-process scoring only — never persisted (gold_rows_data holds
# PolyglossRow dataclasses, not JSON-serializable; the wordform/lexicon lists would bloat every
# per-language result file with a full copy of the gold).
_MANIFEST_INPROCESS_KEYS = ("gold_wordforms", "gold_lexicon", "gold_rows_data")


def _scale(vocab: int) -> tuple[int, int]:
    """Auto-scale (n_roots, test_size) with target-vocabulary size — a flat root count isn't
    comparable across an 800-word-vocabulary pilot language and a 36k-row one (Arapaho): 80 roots
    would floor the data-rich end and be nearly the whole lexicon at the thin end. Roughly a fifth of
    the vocabulary becomes roots (capped, per Polygloss_integration.md §4's "n_roots scaled down"
    guidance vs. eBible's flat 300), a twentieth becomes the held-out test tranche."""
    n_roots = max(60, min(300, vocab // 5))
    test_size = max(20, min(120, vocab // 20))
    return n_roots, test_size


def run_pilot(
    glottocode: str,
    *,
    language: str | None = None,
    fetch: bool = True,
    seconds: float = 90.0,
    n_roots: int | None = None,
    batch: int = 4,
    test_size: int | None = None,
    amb_cap: float = 5.0,
    gold_holdout: int = 300,
) -> dict:
    from engine.grammar import Affix, LangModel, LexEntry
    from induce import tdd

    t0 = time.monotonic()
    manifest = build_pilot(glottocode, language=language, fetch=fetch, gold_holdout=gold_holdout)
    pk = manifest["pair_key"]
    register_pair(pk)

    if n_roots is None or test_size is None:
        auto_roots, auto_test = _scale(manifest["target_word_types"])
        n_roots = n_roots if n_roots is not None else auto_roots
        test_size = test_size if test_size is not None else auto_test

    induction = tdd.run(pk, seconds, n_roots=n_roots, batch=batch, test_size=test_size, amb_cap=amb_cap)

    wordforms = manifest["gold_wordforms"]
    lex_entries = manifest["gold_lexicon"]
    gold_score: dict = {}
    if wordforms:
        model_path = _RESEARCH / "induce" / "out" / f"{pk}_model.json"
        d = json.loads(model_path.read_text(encoding="utf-8"))
        model = LangModel(
            code=pk,
            lexicon=[LexEntry(form=r["form"], gloss=r.get("gloss", "?"), pos=r.get("pos", "noun"),
                              count=r.get("count", 0)) for r in d["roots"]],
            affixes=[Affix(form=a["form"], gloss=a.get("gloss", a["form"]), kind=a["kind"],
                           count=a.get("count", 0), slot_ord=a.get("slot_ord", 1),
                           req_pos=a.get("req_pos", "")) for a in d["affixes"]],
        )
        gold_score = score_pair(model, wordforms, lex_entries)

    persisted_manifest = {k: v for k, v in manifest.items() if k not in _MANIFEST_INPROCESS_KEYS}
    result = {
        "glottocode": glottocode,
        "pair_key": pk,
        "manifest": persisted_manifest,
        "induction": {
            "base_coverage": induction["base_coverage"],
            "final_coverage": induction["final_coverage"],
            "delta": induction["delta"],
            "final_ambiguity": induction["final_ambiguity"],
            "lexicon": induction["lexicon"],
            "morphotactics": induction["morphotactics"],
            "harmony_families": induction["harmony_families"],
            "enumeration_debt": induction["enumeration_debt"],
        },
        "gold_benchmark": gold_score,
        "secs": round(time.monotonic() - t0, 1),
    }
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / f"{pk}_pilot.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glottocode", required=True)
    ap.add_argument("--language", default=None)
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--roots", type=int, default=None, help="default: auto-scaled from vocabulary size")
    ap.add_argument("--test-size", type=int, default=None, help="default: auto-scaled from vocabulary size")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    r = run_pilot(
        args.glottocode, language=args.language, fetch=not args.no_fetch,
        seconds=args.seconds, n_roots=args.roots, test_size=args.test_size,
    )
    gb = r["gold_benchmark"]
    print(f"\n[{r['pair_key']}] pilot done in {r['secs']}s: "
          f"internal coverage {r['induction']['base_coverage']:.3f}->{r['induction']['final_coverage']:.3f}")
    if gb:
        split = r["manifest"]["gold_source_split"]
        note = " (gold from train split — parse_rate is an OPTIMISTIC upper bound, gold surfaces may seed roots)" \
            if split == "train" else " (gold from disjoint test split — contamination-free)"
        print(f"[{r['pair_key']}] gold benchmark ({gb['tested']} held-out words, split={split}){note}:")
        print(f"[{r['pair_key']}]   parse_rate={gb['parse_rate']:.3f} lemma_recall={gb['lemma_recall']:.3f} "
              f"feature_recall={gb['feature_recall']:.3f}")
    else:
        print(f"[{r['pair_key']}] no gold benchmark available (no segmented rows found).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
