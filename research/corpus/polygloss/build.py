"""Build one PolyGloss pilot language into the shape `induce/tdd.py` already knows how to consume.

Implements Polygloss_integration.md §4.3 option (a) — "impersonate an eBible pair": write
`parallel.jsonl` + `glosses.tsv` (same shape `corpus/ebible/build.py` produces) into
`_sources/ebible/pg_<glottocode>/`, then register that directory name in `induce.tdd.PAIR_DIR` (a
plain module-level dict, mutable at call time). Zero changes to `tdd.py`.

**Gold-blindness is the whole point of this benchmark and it is load-bearing here**: `glosses.tsv`
is built ONLY by running `align.aligner.align` (THOT Eflomal / co-occurrence) over
`(translation, transcription)` token pairs — exactly the unlabeled signal the eBible pipeline uses.
The row's own `segmentation`/`glosses` fields (the hand-annotated gold) are NEVER read here; they
flow only into `to_gold.rows_to_wordforms_and_lexicon`, kept in memory for `score.py` to score
against. `golden_sets/pg_<glottocode>/` is **not** written by a benchmark run — per
Polygloss_integration.md §6 steps 4-5, promotion to a real frozen golden set is a deliberate,
separate call (`promote_golden_set`) for a language that earns it, not a side effect of scoring.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from align import align  # noqa: E402

from .convert import is_english_metalanguage, to_parallel_row  # noqa: E402
from .fetch import DEFAULT_CACHE_DIR, fetch_language, load_cached  # noqa: E402
from .orthography import extra_word_chars_for  # noqa: E402
from .schema import PolyglossRow  # noqa: E402
from .to_gold import rows_to_wordforms_and_lexicon, write_pilot_gold  # noqa: E402

EBIBLE_SOURCES = _RESEARCH / "_sources" / "ebible"


def pair_key(glottocode: str) -> str:
    return f"pg_{glottocode}"


def _load_split(glottocode: str, split: str, *, cache_dir: Path, fetch: bool) -> list[PolyglossRow]:
    if fetch:
        fetch_language(glottocode, cache_dir=cache_dir, split=split)
    try:
        raw = load_cached(glottocode, cache_dir=cache_dir, split=split)
    except FileNotFoundError:
        return []
    return [PolyglossRow.from_dict(r) for r in raw]


def load_gold_rows(
    glottocode: str, train_eng: list[PolyglossRow], *, cache_dir: Path = DEFAULT_CACHE_DIR,
    fetch: bool = True, gold_holdout: int = 300,
) -> tuple[list[PolyglossRow], str]:
    """-> (gold_rows, gold_source_split). Prefers the corpus's own `test` split (genuinely disjoint
    from `train`); falls back to holding out up to `gold_holdout` segmented `train_eng` rows if `test`
    has none for this language (many long-tail languages only appear in `train`). Factored out of
    `build_pilot` so a re-scoring pass can rebuild the exact same gold selection from cache without
    re-fetching/re-aligning (e.g. after a `to_gold.py` normalization fix)."""
    test_rows = _load_split(glottocode, "test", cache_dir=cache_dir, fetch=fetch)
    test_eng_segmented = [r for r in test_rows if is_english_metalanguage(r) and r.is_segmented]
    if test_eng_segmented:
        return test_eng_segmented[:gold_holdout], "test"
    return [r for r in train_eng if r.is_segmented][:gold_holdout], "train"


def build_pilot(
    glottocode: str,
    *,
    language: str | None = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    fetch: bool = True,
    backend: str = "auto",
    gold_holdout: int = 300,
) -> dict:
    """Fetch (if needed) -> filter to English metalanguage -> THOT-align (gold-blind) -> write the
    `_sources/ebible/pg_<glottocode>/` training corpus. Returns a manifest dict — including the
    held-out gold as in-memory `gold_wordforms`/`gold_lexicon` (NOT persisted to `golden_sets/`; see
    `promote_golden_set` for that deliberate, separate step). Raises if there are no usable
    English-metalanguage rows.

    Gold reserve: see `load_gold_rows`. Held-out rows still contribute their raw (translation,
    transcription) tokens to the training corpus — that carries frequency information only, never
    segmentation/gloss labels, so it doesn't break gold-blindness (see module docstring).
    """
    pk = pair_key(glottocode)
    train_rows = _load_split(glottocode, "train", cache_dir=cache_dir, fetch=fetch)
    if not train_rows:
        raise RuntimeError(f"no train rows for {glottocode!r}")
    train_eng = [r for r in train_rows if is_english_metalanguage(r)]
    if not train_eng:
        raise RuntimeError(f"no English-metalanguage train rows for {glottocode!r}")

    gold_rows, gold_source_split = load_gold_rows(
        glottocode, train_eng, cache_dir=cache_dir, fetch=fetch, gold_holdout=gold_holdout
    )

    extra = extra_word_chars_for(glottocode)
    parallel_rows = [to_parallel_row(r, extra_word_chars=extra) for r in train_eng]
    table, used_backend = align(parallel_rows, backend=backend)

    out_dir = EBIBLE_SOURCES / pk
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "parallel.jsonl").write_text(
        "".join(
            json.dumps({"ref": r.id, "src": src, "tgt": tgt}, ensure_ascii=False) + "\n"
            for r, (src, tgt) in zip(train_eng, parallel_rows)
        ),
        encoding="utf-8",
    )
    with (out_dir / "glosses.tsv").open("w", encoding="utf-8") as f:
        f.write("target\tsource\tprob\tcount\n")
        for tw, cands in table:
            g = cands[0]
            f.write(f"{tw}\t{g.source_word}\t{g.prob}\t{g.count}\n")

    lang = language or next((r.language for r in train_eng if r.language), glottocode)
    gold_wordforms, gold_lexicon = rows_to_wordforms_and_lexicon(gold_rows, glottocode=glottocode)

    manifest = {
        "glottocode": glottocode,
        "language": lang,
        "pair_key": pk,
        "rows_train_total": len(train_rows),
        "rows_train_english_meta": len(train_eng),
        "rows_train_segmented": sum(1 for r in train_eng if r.is_segmented),
        "gold_rows": len(gold_rows),
        "gold_source_split": gold_source_split,
        "align_backend": used_backend,
        "target_word_types": len(table.table),
        "gold_counts": {"wordforms": len(gold_wordforms), "lexicon": len(gold_lexicon)},
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # gold_wordforms/gold_lexicon are returned for in-process scoring only — deliberately NOT part of
    # the persisted manifest.json (that file only records counts, not the gold content itself).
    return {**manifest, "gold_wordforms": gold_wordforms, "gold_lexicon": gold_lexicon, "gold_rows_data": gold_rows}


def register_pair(pk: str) -> None:
    """Add `pk` to `induce.tdd.PAIR_DIR` (mutable dict) so `induce/tdd.py` treats the pilot corpus as
    an eBible pair — the impersonate-a-pair adapter, Polygloss_integration.md §4.3 option (a)."""
    from induce import tdd

    tdd.PAIR_DIR[pk] = pk


def promote_golden_set(glottocode: str, gold_rows: list[PolyglossRow], *, language: str, source: str = "polygloss") -> dict:
    """Explicitly promote a pilot language's held-out gold to a real, frozen `golden_sets/pg_<
    glottocode>/` directory — Polygloss_integration.md §6 step 4: a deliberate call for a language
    that "earns it" after reviewing its benchmark score, never an automatic side effect of scoring."""
    return write_pilot_gold(pair_key(glottocode), gold_rows, glottocode=glottocode, language=language, source=source)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glottocode", required=True)
    ap.add_argument("--language", default=None)
    ap.add_argument("--backend", default="auto", help="auto|eflomal|cooccur")
    ap.add_argument("--no-fetch", action="store_true", help="use already-cached rows")
    ap.add_argument("--gold-holdout", type=int, default=300)
    args = ap.parse_args(argv)
    m = build_pilot(
        args.glottocode,
        language=args.language,
        fetch=not args.no_fetch,
        backend=args.backend,
        gold_holdout=args.gold_holdout,
    )
    print(
        f"[{m['pair_key']}] {m['language']}: {m['rows_train_english_meta']}/{m['rows_train_total']} "
        f"english-meta train rows, {m['target_word_types']} target types (backend={m['align_backend']}); "
        f"gold={m['gold_rows']} rows from {m['gold_source_split']} split"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
