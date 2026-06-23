"""Build a golden-set scaffold for an English↔target eBible pair.

fetch → read (verse-aligned, NT, tokenized) → align (word glosses) → candidate `bilingual/*` sense
links + manifest. Outputs land under `<out>/<eng>__<tgt>/`. Raw sources + large derived files are
git-ignored (regenerable); the manifest + glosses + candidate links are the committed gold.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# make research/ importable (align, proposal, …) regardless of CWD
_RESEARCH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_RESEARCH))

from align import align, gloss_table_to_sense_link_ops  # noqa: E402

from corpus.ebible.config import ENGLISH_ID, TARGETS  # noqa: E402
from corpus.ebible.fetch import DEFAULT_SRC_DIR, fetch_text, fetch_vref  # noqa: E402
from corpus.ebible.read import parallel_rows  # noqa: E402


def build_pair(
    target: str,
    *,
    src_dir: Path = DEFAULT_SRC_DIR,
    out_dir: Path | None = None,
    backend: str = "auto",
    fetch: bool = True,
) -> dict:
    if target not in TARGETS:
        raise SystemExit(f"unknown target {target!r}; known: {sorted(TARGETS)}")
    tgt_id = TARGETS[target]
    out_dir = out_dir or (src_dir / f"{ENGLISH_ID}__{tgt_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    if fetch:
        vref = fetch_vref(src_dir)
        eng = fetch_text(ENGLISH_ID, src_dir)
        tgt = fetch_text(tgt_id, src_dir)
    else:
        vref, eng, tgt = src_dir / "vref.txt", src_dir / f"{ENGLISH_ID}.txt", src_dir / f"{tgt_id}.txt"

    rows = parallel_rows(vref, eng, tgt, nt_only=True)
    pairs = [(r.src, r.tgt) for r in rows]
    table, used = align(pairs, backend=backend)
    ops = gloss_table_to_sense_link_ops(table, min_count=3)

    # write parallel rows (regenerable, may be large) + derived gold
    (out_dir / "parallel.jsonl").write_text(
        "".join(json.dumps({"ref": r.ref, "src": r.src, "tgt": r.tgt}, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    with (out_dir / "glosses.tsv").open("w", encoding="utf-8") as f:
        f.write("target\tsource\tprob\tcount\n")
        for tw, cands in table:
            g = cands[0]
            f.write(f"{tw}\t{g.source_word}\t{g.prob}\t{g.count}\n")
    (out_dir / "sense_links.candidates.json").write_text(
        json.dumps({"ops": ops}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest = {
        "english_id": ENGLISH_ID,
        "target_id": tgt_id,
        "target_key": target,
        "nt_only": True,
        "verses_aligned": len(rows),
        "target_word_types": len(table.table),
        "align_backend": used,
        "candidate_sense_links": len(ops),
        "source": "BibleNLP/ebible (redistributable corpus, verse-aligned via vref.txt)",
        "note": "Raw text + parallel.jsonl are git-ignored (regenerable). License: non-profit/charity use.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", nargs="+", default=["swh", "ind", "tgl", "spa"], help=f"targets: {sorted(TARGETS)}")
    ap.add_argument("--backend", default="auto", help="auto|hmm|cooccur")
    ap.add_argument("--no-fetch", action="store_true", help="use already-downloaded sources")
    args = ap.parse_args(argv)
    for t in args.pair:
        m = build_pair(t, backend=args.backend, fetch=not args.no_fetch)
        print(
            f"[{t}] {m['english_id']} <-> {m['target_id']}: {m['verses_aligned']} verses, "
            f"{m['target_word_types']} target types, {m['candidate_sense_links']} candidate links "
            f"(backend={m['align_backend']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
