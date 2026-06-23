"""Morpheme-level alignment (GREEDY, offline) — SUPERSEDED for the verified path by
``align/morph_align_hc.py``.

  This module segments each word by a **greedy string match** against the induced model and emits a flat
  morpheme→gloss table with no markers/provenance. The verified path is ``align/morph_align_hc.py``: it
  segments from the **HC parse** (the exact gloss line → grammar constructs, root recovered by peeling
  affixes), attaches per-morpheme markers + THOT probabilities, and routes accept/defer to
  ``deltas/`` / ``deferrals/``. Keep THIS module only as the no-HC, offline/co-occurrence quick path; use
  ``morph_align_hc.py`` for anything that should be trusted. See the OpenSpec ``morpheme-alignment`` change.

The base pipeline aligns English to whole TARGET WORDS, so it glosses to the lemma and an affix never
gets its own gloss. Once the cycle has a grammar, we can do better: segment each target word into its
morphemes (root + affixes, via the induced grammar) and re-align English against the **morphemes**.
Now `-ni` aligns to "in", `-s`/`meN-`/etc. align to the grammatical English they correlate with — so
affixes get real function glosses and roots get sharper ones. This is the feedback edge of the
steady-state virtuous cycle; its output (a morpheme→gloss table, esp. affix functions) re-seeds the
next cycle and is the evidence the LLM propose step (llm_propose.py) reasons over.

Standalone: reconstructs the model from `cycle/out/<pair>_model.json` (written by tdd.py) and the pair's
`parallel.jsonl`. Default backend is the offline co-occurrence aligner; `--backend hmm` uses THOT.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RESEARCH))

from align import align  # noqa: E402
from engine.grammar import Affix, LangModel, LexEntry  # noqa: E402

EBIBLE = _RESEARCH / "_sources" / "ebible"
OUT = Path(__file__).resolve().parent / "out"
PAIR_DIR = {
    "swh": "eng-engwebp__swh-swhulb", "ind": "eng-engwebp__ind-indags",
    "tgl": "eng-engwebp__tgl-tglulb", "spa": "eng-engwebp__spa-spaRV1909",
}


def load_model(pair: str) -> LangModel:
    """Reconstruct the induced grammar from the cycle's `out/<pair>_model.json` dump."""
    data = json.loads((OUT / f"{pair}_model.json").read_text(encoding="utf-8"))
    lex = [LexEntry(form=r["form"], gloss=r["gloss"], pos=r.get("pos", "root"), count=r.get("count", 0))
           for r in data["roots"]]
    aff = [Affix(form=a["form"], gloss=a["gloss"], kind=a["kind"], count=a.get("count", 0),
                 slot_ord=a.get("slot_ord", 1), req_pos=a.get("req_pos", "")) for a in data["affixes"]]
    return LangModel(code=pair, lexicon=lex, affixes=aff)


def load_parallel(pair: str) -> list[tuple[list[str], list[str]]]:
    p = EBIBLE / PAIR_DIR[pair] / "parallel.jsonl"
    rows: list[tuple[list[str], list[str]]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows.append((list(r["src"]), list(r["tgt"])))
    return rows


def segment_word(w: str, roots: list[str], suff: list[str], pref: list[str], infx: list[str]) -> list[tuple[str, str]]:
    """Greedily segment a surface word into [(morpheme, role)], role ∈ {prefix,root,infix,suffix}.

    Finds the longest contiguous known root, then the prefixes before it (surface order) and suffixes
    after it; if no contiguous root fits, tries an infixed root (root[0] + INFIX + root[1:]).
    """
    for r in roots:
        i = w.find(r)
        if i < 0:
            continue
        pre, suf = w[:i], w[i + len(r):]
        out: list[tuple[str, str]] = []
        pos = 0  # prefixes, surface order (longest match from the left)
        while pos < len(pre):
            m = next((p for p in pref if pre.startswith(p, pos)), None)
            if not m:
                out.append((pre[pos:], "prefix"))
                break
            out.append((m, "prefix")); pos += len(m)
        out.append((r, "root"))
        pos = 0  # suffixes, surface order
        while pos < len(suf):
            m = next((s for s in suff if suf.startswith(s, pos)), None)
            if not m:
                out.append((suf[pos:], "suffix"))
                break
            out.append((m, "suffix")); pos += len(m)
        return out
    # no contiguous root → try an infixed root
    for r in roots:
        if len(r) >= 4 and w[:1] == r[:1] and w.endswith(r[1:]):
            inf = w[1: len(w) - (len(r) - 1)]
            if inf in infx:
                return [(r, "root"), (inf, "infix")]
    return [(w, "root")]


def morpheme_gloss_table(rows: list[tuple[list[str], list[str]]], model: LangModel,
                         backend: str = "cooccur") -> tuple[dict[str, dict], str]:
    """Re-align English ↔ target MORPHEMES; return {morpheme: {gloss, prob, count, role}}, backend_used."""
    roots = sorted({e.form for e in model.lexicon if len(e.form) >= 3}, key=len, reverse=True)
    suff = sorted({a.form for a in model.affixes if a.kind == "suffix"}, key=len, reverse=True)
    pref = sorted({a.form for a in model.affixes if a.kind == "prefix"}, key=len, reverse=True)
    infx = sorted({a.form for a in model.affixes if a.kind == "infix"}, key=len, reverse=True)
    role_of = {a.form: a.kind for a in model.affixes}

    morph_rows: list[tuple[list[str], list[str]]] = []
    for src, tgt in rows:
        morphs: list[str] = []
        for word in tgt:
            morphs.extend(m for m, _ in segment_word(word, roots, suff, pref, infx))
        morph_rows.append((src, morphs))

    table, used = align(morph_rows, backend=backend)
    out: dict[str, dict] = {}
    for tw, cands in table:
        if cands:
            g = cands[0]
            out[tw] = {"gloss": g.source_word, "prob": round(g.prob, 4), "count": g.count,
                       "role": role_of.get(tw, "root")}
    return out, used


def run(pair: str, backend: str = "cooccur") -> dict:
    model = load_model(pair)
    rows = load_parallel(pair)
    morph_gloss, used = morpheme_gloss_table(rows, model, backend=backend)
    OUT.mkdir(exist_ok=True)
    tsv = OUT / f"{pair}_morpheme_glosses.tsv"
    with tsv.open("w", encoding="utf-8") as f:
        f.write("morpheme\trole\tgloss\tprob\tcount\n")
        for m, d in sorted(morph_gloss.items(), key=lambda kv: -kv[1]["count"]):
            f.write(f"{m}\t{d['role']}\t{d['gloss']}\t{d['prob']}\t{d['count']}\n")
    affix_glosses = {a.form: morph_gloss.get(a.form, {}).get("gloss")
                     for a in model.affixes if morph_gloss.get(a.form)}
    summary = {"pair": pair, "backend": used, "morphemes": len(morph_gloss),
               "affixes_glossed": len(affix_glosses), "affix_glosses": affix_glosses}
    (OUT / f"{pair}_morpheme_glosses.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--backend", default="cooccur", help="cooccur|hmm|auto")
    args = ap.parse_args(argv)
    s = run(args.pair, backend=args.backend)
    print(f"[{args.pair}] morpheme alignment ({s['backend']}): {s['morphemes']} morphemes glossed, "
          f"{s['affixes_glossed']} affixes got a gloss")
    shown = list(s["affix_glosses"].items())[:20]
    print("  affix glosses: " + ", ".join(f"{m}={g}" for m, g in shown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
