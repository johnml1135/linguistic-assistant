"""THOT-on-morphs paradigm study harness (`thot-on-morphs.md`).

For each pair: run P0 ONCE (the production `induce.tdd.run` loop, unmodified) to get a base grammar, freeze
a held-out test set + silver gold from that snapshot, then run every paradigm's alignment-table
construction through the SAME cotrain-shaped root-discovery loop (`induce.cotrain.propose_roots` +
`_roundtrip_keep` + `_coverage`, reused unmodified) starting from that one frozen snapshot — so paradigms
differ ONLY in how the alignment table is built, never in which grammar they started from or how long they
ran. Writes one JSON file per (pair, paradigm) cell to `align/out/thot_on_morphs/`.

Paradigms: P0 (no THOT) is scored but not run per-paradigm (see above). P1 identity (today's `cotrain.py`
default), P2 unsupervised BPE English, P3 P2 + harmony-class target canonicalization, P4 guided English
split, P5 hybrid (guided first, BPE fallback on unresolved long residues), P6 factored (POS/MSA-class
pooling on affixes, Koehn & Hoang 2007) — see thot-on-morphs-report.md for citations.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from align import class_key, segment_en  # noqa: E402
from align.aligner import align  # noqa: E402
from align.contract import GlossTable  # noqa: E402
from align.morph_align_hc import _verses, build_streams  # noqa: E402
from align.silver_gold import build_silver_gold  # noqa: E402
from induce import cotrain, tdd  # noqa: E402
from engine.grammar import LexEntry  # noqa: E402
from gold.phonology_gold import phon_feats as gold_phon_feats  # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "thot_on_morphs"
OUT.mkdir(parents=True, exist_ok=True)

PAIRS = ["swh", "ind", "tgl", "spa", "tur", "rus", "hin", "vie"]
PARADIGMS = ["P1", "P2", "P3", "P4", "P5", "P6"]

BPE_MERGES = 300
SAMPLE_VERSES = 200
COTRAIN_WORDS = 600
CYCLES = 2
GATE = cotrain.GATE
AMB_CAP = 8.0
HELD_OUT_N = 150
SILVER_GOLD_N = 40


# --------------------------------------------------------------------------- table builders (the paradigm)
def _en_freqs(morph_rows: list[tuple[list[str], list[str]]]) -> Counter:
    c: Counter = Counter()
    for src, _tgt in morph_rows:
        c.update(src)
    return c


def table_p1(pair: str, model, sample: int) -> GlossTable:
    """Identity — today's cotrain.py default: target HC-morphemes vs whole English words."""
    return cotrain._align_table(pair, model, sample)


def _base_morph_rows(pair: str, model, sample: int):
    verses = _verses(pair, sample)
    _streams, morph_rows = build_streams(pair, model, verses)
    return morph_rows


def table_p2(pair: str, model, sample: int) -> GlossTable:
    """Unsupervised BPE on English, target stays HC-morphemes."""
    morph_rows = _base_morph_rows(pair, model, sample)
    merges = segment_en.learn_bpe(_en_freqs(morph_rows), BPE_MERGES)
    rows = [(segment_en.bpe_segment(src, merges), tgt) for src, tgt in morph_rows]
    table, _used = align(rows, backend="eflomal", allow_cooccur_fallback=False)
    return table


def table_p3(pair: str, model, sample: int) -> GlossTable:
    """P2's English BPE + harmony-class canonicalization of target morphemes (§4 class_key)."""
    morph_rows = _base_morph_rows(pair, model, sample)
    merges = segment_en.learn_bpe(_en_freqs(morph_rows), BPE_MERGES)
    canon = class_key.canonical_map(model, pair)
    rows = [(segment_en.bpe_segment(src, merges), [canon.get(t, t) for t in tgt]) for src, tgt in morph_rows]
    table, _used = align(rows, backend="eflomal", allow_cooccur_fallback=False)
    return table


def table_p4(pair: str, model, sample: int) -> GlossTable:
    """Guided English split, gated on cross-lingual evidence from a reverse P1-style table."""
    morph_rows = _base_morph_rows(pair, model, sample)
    rev_rows = [(tgt, src) for src, tgt in morph_rows]
    rev_table, _used = align(rev_rows, backend="eflomal", allow_cooccur_fallback=False)
    en_freqs = _en_freqs(morph_rows)
    split_map = segment_en.guided_split_map(en_freqs, rev_table)
    rows = [(segment_en.guided_segment(src, split_map), tgt) for src, tgt in morph_rows]
    table, _used = align(rows, backend="eflomal", allow_cooccur_fallback=False)
    return table, split_map


def table_p5(pair: str, model, sample: int) -> GlossTable:
    """Hybrid: guided split where bilingual evidence supports it, BPE fallback on unresolved long
    residues, plus P3's target-side class canonicalization. A genuinely new comparison cell, not one of
    the four originally-planned paradigms."""
    morph_rows = _base_morph_rows(pair, model, sample)
    rev_rows = [(tgt, src) for src, tgt in morph_rows]
    rev_table, _used = align(rev_rows, backend="eflomal", allow_cooccur_fallback=False)
    en_freqs = _en_freqs(morph_rows)
    split_map = segment_en.guided_split_map(en_freqs, rev_table)
    merges = segment_en.learn_bpe(en_freqs, BPE_MERGES)
    canon = class_key.canonical_map(model, pair)

    def seg(tokens: list[str]) -> list[str]:
        out = []
        for t in segment_en.guided_segment(tokens, split_map):
            out.extend(segment_en.apply_bpe(t, merges) if len(t) > 6 else [t])
        return out

    rows = [(seg(src), [canon.get(t, t) for t in tgt]) for src, tgt in morph_rows]
    table, _used = align(rows, backend="eflomal", allow_cooccur_fallback=False)
    return table


def table_p6(pair: str, model, sample: int) -> GlossTable:
    """Factored (Koehn & Hoang 2007): affixes canonicalized to their learned POS/MSA class (`req_pos`)
    instead of surface form; roots stay literal (content morphemes keep their lexical identity, only
    grammatical morphemes are pooled by function class) — a morphosyntactic-class axis, distinct from
    P3's phonological-class axis."""
    morph_rows = _base_morph_rows(pair, model, sample)
    req_pos = {a.form: a.req_pos for a in model.affixes if a.req_pos}
    kind_of = {a.form: a.kind for a in model.affixes}

    def factor(tok: str) -> str:
        if tok in kind_of and req_pos.get(tok):
            return f"{kind_of[tok]}:{req_pos[tok]}"
        return tok

    rows = [(src, [factor(t) for t in tgt]) for src, tgt in morph_rows]
    table, _used = align(rows, backend="eflomal", allow_cooccur_fallback=False)
    return table


TABLE_BUILDERS = {"P1": table_p1, "P2": table_p2, "P3": table_p3, "P4": table_p4,
                  "P5": table_p5, "P6": table_p6}


# --------------------------------------------------------------------------- generic cotrain-shaped loop
def run_variant(pair: str, base_model, words: list[str], build_table, *, cycles: int = CYCLES,
                gate: float = GATE, amb_cap: float = AMB_CAP, sample: int = SAMPLE_VERSES) -> dict:
    """Mirrors `induce.cotrain.cotrain`'s loop body exactly, except the alignment table comes from
    `build_table(pair, model, sample)` instead of the hardcoded `_align_table` — the ONLY axis of
    variation between paradigms. Reuses `cotrain.propose_roots`/`_clone`/`_coverage` unmodified."""
    model = cotrain._clone(base_model)
    pf = gold_phon_feats(pair, model.charset)
    history, total_added, split_map_info = [], [], None
    t0 = time.monotonic()
    cov0, _amb0 = cotrain._coverage(model, words, pf)
    for k in range(1, cycles + 1):
        from engine.hc import run_parse
        parsed = run_parse(model, words, chunk_size=25, chunk_timeout=20, phon_feats=pf)
        unparsed = [w for w in words if not parsed.get(w)]
        built = build_table(pair, model, sample)
        table = built[0] if isinstance(built, tuple) else built
        if isinstance(built, tuple):
            split_map_info = len(built[1])
        known = {e.form for e in model.lexicon}
        pre = [a.form for a in model.affixes if a.kind == "prefix"]
        suf = [a.form for a in model.affixes if a.kind == "suffix"]
        proposals = cotrain.propose_roots(unparsed, table, gate=gate, known_forms=known,
                                          prefixes=pre, suffixes=suf)
        if not proposals:
            history.append({"cycle": k, "unparsed": len(unparsed), "proposed": 0, "kept": False,
                            "reason": "no confident proposals"})
            break
        trial = cotrain._clone(model)
        for f, (g, _p, _s) in proposals.items():
            trial.lexicon.append(LexEntry(form=f, gloss=g, pos="root", count=0))
        cov1, amb1 = cotrain._coverage(trial, words, pf)
        kept = cov1 > cov0 + 1e-9 and amb1 <= amb_cap
        history.append({"cycle": k, "unparsed": len(unparsed), "proposed": len(proposals),
                        "cov_before": round(cov0, 4), "cov_after": round(cov1, 4),
                        "delta": round(cov1 - cov0, 4), "amb": round(amb1, 2), "kept": kept})
        if not kept:
            break
        model, cov0 = trial, cov1
        total_added.extend({"form": f, "gloss": g, "prob": p} for f, (g, p, _s) in proposals.items())
    return {"model": model, "history": history, "roots_added": len(total_added), "added": total_added,
            "final_coverage": cov0, "secs": round(time.monotonic() - t0, 1),
            "split_map_size": split_map_info}


# --------------------------------------------------------------------------- per-pair driver
def freeze_held_out(pair: str, model, n: int = HELD_OUT_N) -> list[str]:
    ranked = [w for w, _ in tdd.load_freqs(pair).most_common() if len(w) >= 2]
    known = {e.form for e in model.lexicon}
    return [w for w in ranked if w not in known][:n]


def score(pair: str, model, held_out: list[str], glosses: dict[str, str]) -> dict:
    pf = gold_phon_feats(pair, model.charset)
    cov, amb = tdd.coverage(model, held_out, pf)
    from induce.phonology import enumeration_debt as _enumeration_debt
    fams = tdd.harmony_families([a.form for a in model.affixes])
    debt = _enumeration_debt(fams)
    gold = build_silver_gold(held_out, glosses, n=SILVER_GOLD_N)
    from induce.gold import score_gold
    gold_result = score_gold(model, gold, phon_feats=pf) if gold else {"n": 0}
    return {"coverage": round(cov, 4), "ambiguity": round(amb, 2), "enumeration_debt": debt,
            "gold": gold_result, "roots": len(model.lexicon), "affixes": len(model.affixes)}


def run_pair(pair: str, *, p0_seconds: float = 60.0) -> dict:
    out_dir = OUT
    p0_path = out_dir / f"{pair}_P0.json"
    if p0_path.exists():
        cell = json.loads(p0_path.read_text(encoding="utf-8"))
        model = tdd._load_prior_model(pair)
        if model is None or not model.lexicon:
            raise RuntimeError(f"{pair}: P0 result cached but induce/out/{pair}_model.json missing")
    else:
        t0 = time.monotonic()
        result = tdd.run(pair, seconds=p0_seconds, n_roots=300, batch=4, test_size=120, amb_cap=5.0)
        model = tdd._load_prior_model(pair)
        cell = {"pair": pair, "paradigm": "P0", "secs": round(time.monotonic() - t0, 1),
                "tdd_result": result}
        p0_path.write_text(json.dumps(cell, ensure_ascii=False, indent=2), encoding="utf-8")

    held_out = freeze_held_out(pair, model)
    (out_dir / f"{pair}_held_out.json").write_text(json.dumps(held_out, ensure_ascii=False), encoding="utf-8")
    glosses = tdd.load_glosses(pair)
    ranked = [w for w, _ in tdd.load_freqs(pair).most_common() if len(w) >= 2]
    words = ranked[:COTRAIN_WORDS]

    cell["score"] = score(pair, model, held_out, glosses)
    p0_path.write_text(json.dumps(cell, ensure_ascii=False, indent=2), encoding="utf-8")

    results = {"P0": cell}
    for name in PARADIGMS:
        out_path = out_dir / f"{pair}_{name}.json"
        if out_path.exists():
            results[name] = json.loads(out_path.read_text(encoding="utf-8"))
            print(f"[{pair}] {name}: cached, skip")
            continue
        try:
            variant = run_variant(pair, model, words, TABLE_BUILDERS[name])
            sc = score(pair, variant["model"], held_out, glosses)
            cell_out = {"pair": pair, "paradigm": name, "secs": variant["secs"],
                        "history": variant["history"], "roots_added": variant["roots_added"],
                        "added": variant["added"][:30], "split_map_size": variant["split_map_size"],
                        "score": sc}
        except Exception as e:  # a paradigm cell failing must not abort the pair's other cells
            import traceback
            cell_out = {"pair": pair, "paradigm": name, "error": str(e),
                        "traceback": traceback.format_exc()[-2000:]}
        out_path.write_text(json.dumps(cell_out, ensure_ascii=False, indent=2), encoding="utf-8")
        results[name] = cell_out
        print(f"[{pair}] {name}: "
              + (f"error: {cell_out.get('error')}" if "error" in cell_out
                 else f"cov {cell_out['score']['coverage']:.3f} roots+{cell_out['roots_added']} "
                      f"secs={cell_out['secs']}"))
    return results


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pairs", nargs="*", default=PAIRS)
    ap.add_argument("--p0-seconds", type=float, default=60.0)
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for pair in args.pairs:
        print(f"=== {pair} ===")
        run_pair(pair, p0_seconds=args.p0_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
