"""Re-score the already-induced pilot models against gold, without re-running induction.

Used after a gold-normalization fix (`to_gold.py`'s `parse_surface`, added once we found that raw
gold surfaces mismatched training tokens on case and stray punctuation — see
Polygloss_integration.md). Rebuilds each language's gold selection from the cached PolyGloss rows
(`load_gold_rows`, no re-fetch/re-align needed) and re-scores the model already saved at
`induce/out/pg_<glottocode>_model.json`, then rewrites `out/PILOT_REPORT.md` from the updated results.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from .build import _load_split, load_gold_rows, pair_key  # noqa: E402
from .convert import is_english_metalanguage  # noqa: E402
from .run_batch import LANGUAGES, OUT_DIR, write_report  # noqa: E402
from .score import score_pair  # noqa: E402
from .to_gold import rows_to_wordforms_and_lexicon  # noqa: E402


def rescore_language(glottocode: str, *, gold_holdout: int = 300) -> tuple[list[dict], list[dict]]:
    """Rebuild (gold_wordforms, gold_lexicon) for `glottocode` from cache, matching exactly what
    `build_pilot` selected the first time (same split preference, same holdout size)."""
    train_rows = _load_split(glottocode, "train", cache_dir=_default_cache(), fetch=False)
    train_eng = [r for r in train_rows if is_english_metalanguage(r)]
    gold_rows, gold_source_split = load_gold_rows(
        glottocode, train_eng, cache_dir=_default_cache(), fetch=False, gold_holdout=gold_holdout
    )
    return rows_to_wordforms_and_lexicon(gold_rows, glottocode=glottocode)


def _default_cache():
    from .fetch import DEFAULT_CACHE_DIR

    return DEFAULT_CACHE_DIR


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from engine.grammar import Affix, LangModel, LexEntry

    old_results = json.loads((OUT_DIR / "batch_results.json").read_text(encoding="utf-8"))
    by_code = {r["glottocode"]: r for r in old_results if r.get("status") == "ok"}

    new_results = []
    for glottocode, language, note in LANGUAGES:
        old = by_code.get(glottocode)
        if old is None:
            print(f"[{glottocode}] skipped (no prior successful run)")
            continue
        t0 = time.monotonic()
        pk = pair_key(glottocode)
        wordforms, lex_entries = rescore_language(glottocode)
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
        gold_score = score_pair(model, wordforms, lex_entries) if wordforms else {}
        r = dict(old)
        r["gold_benchmark"] = gold_score
        r["secs"] = round(old["secs"] + (time.monotonic() - t0), 1)
        new_results.append(r)
        print(f"[{pk}] rescored: parse_rate={gold_score.get('parse_rate')} "
              f"lemma_recall={gold_score.get('lemma_recall')} feature_recall={gold_score.get('feature_recall')}")

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "batch_results.json").write_text(
        json.dumps(new_results, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    write_report(new_results, OUT_DIR / "PILOT_REPORT.md")
    print(f"\nWrote {OUT_DIR / 'PILOT_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
