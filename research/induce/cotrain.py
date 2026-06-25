"""THOT <-> HC co-training loop — mutually-updating cycles that raise HC coverage.

The two estimators feed each other:
  HC  -> defines the coverage gap : the frequent words HC currently cannot segment (unparsed).
  THOT-> fills the gap            : aligned over HC's CURRENT segmentation, it says what each unparsed word
                                    means; a confident, CONTENT-word-aligned proposal becomes a glossed root.
  HC  -> parses more next cycle   : the new roots change what parses AND how other words segment, so the next
                                    HC pass yields a new gap and THOT re-aligns over the new streams.

This is the loop the move/prune interventions lacked: they rearranged existing morphemes (no coverage
effect / coverage crash); this one ADDS the lexicon HC was missing, gated by THOT confidence so it stays
real. Each cycle is KEPT only if coverage rises (coverage-guarded — the loop can never lower the metric),
and it stops at a fixpoint (no confident proposals, or no gain).

Measured on swh (probe, 2026-06-25): cycle-1 target coverage 0.598 -> 0.818 (+0.22) from 107 correct
THOT-glossed roots (enzi=throne, daudi=david, mkate=bread, ushuhuda=testimony, ...), +0.02 generalization
to a disjoint held-out set, ambiguity flat (no over-generation). The glossed roots also emit as deltas.

Run:  python -m induce.cotrain --pair swh --cycles 6
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from engine.grammar import LexEntry, LangModel   # noqa: E402
from review import langknow                       # noqa: E402

GATE = 0.5            # min THOT alignment probability to trust a root proposal
MIN_SRC_LEN = 3       # ignore alignments to very short pivot tokens


def _residue(word: str, prefixes: list[str], suffixes: list[str]) -> str:
    """Peel ONE longest-matching known prefix and ONE longest-matching known suffix off an unparsed word to
    recover its likely ROOT. Using HC's own affix inventory to strip is the mutual half on the segmentation
    side — the recovered root then generalises to every other inflected form of the same lexeme."""
    r = word
    for p in prefixes:                       # pre-sorted longest-first
        if r.startswith(p) and len(r) - len(p) >= 2:
            r = r[len(p):]
            break
    for s in suffixes:
        if r.endswith(s) and len(r) - len(s) >= 2:
            r = r[: -len(s)]
            break
    return r


def propose_roots(unparsed: list[str], table, *, pivot: str = "en", gate: float = GATE,
                  known_forms: set[str] | None = None, prefixes: list[str] | None = None,
                  suffixes: list[str] | None = None) -> dict[str, tuple[str, float, tuple]]:
    """THOT proposals for the unparsed words: keep those aligned to a CONTENT pivot word above `gate`.
    A content-word alignment signals a missing LEXEME (root); a function-word alignment is grammatical
    (an affix's job, not a root) and is left for the morphotactics path. When affix inventories are given,
    the proposed root FORM is the affix-stripped residue (generalises across inflected forms); otherwise the
    whole word. Returns {root_form -> (gloss, prob, source_words)} (deduped, max prob). Pure given table."""
    function = langknow.function_words(pivot)
    known = known_forms or set()
    strip = bool(prefixes or suffixes)
    pre = sorted(prefixes or [], key=len, reverse=True)
    suf = sorted(suffixes or [], key=len, reverse=True)
    acc: dict[str, tuple[str, float, set]] = {}
    for w in unparsed:
        b = table.best(w)
        if not (b and b.prob >= gate and b.source_word not in function and len(b.source_word) >= MIN_SRC_LEN):
            continue
        form = _residue(w, pre, suf) if strip else w
        if len(form) < 2 or form in known:
            continue
        cur = acc.get(form)
        if cur is None:
            acc[form] = (b.source_word, round(b.prob, 3), {w})
        else:
            g, p, srcs = cur
            srcs.add(w)
            acc[form] = (b.source_word if b.prob > p else g, max(round(b.prob, 3), p), srcs)
    return {f: (g, p, tuple(sorted(s))) for f, (g, p, s) in acc.items()}


def _coverage(model, words, pf):
    from induce.tdd import coverage
    return coverage(model, words, phon_feats=pf)


def _align_table(pair: str, model, sample: int):
    """THOT over the CURRENT HC segmentation — the mutual half: HC's parse decides the alignment units."""
    from align.morph_align_hc import build_streams, _verses
    from align import align
    verses = _verses(pair, sample)
    _streams, morph_rows = build_streams(pair, model, verses)
    table, _used = align(morph_rows, backend="hmm", allow_cooccur_fallback=False)
    return table


def _roundtrip_keep(base: LangModel, proposals: dict, pf) -> dict:
    """(switch a) Keep only roots that actually let HC parse a source word they came from — a round-trip
    correctness gate that drops residues whose segmentation HC can't realise. Batch: add all, parse the
    union of source words, credit a root if >=1 of its source words now parses."""
    from engine.hc import run_parse
    trial = _clone(base)
    for f, (g, _p, _s) in proposals.items():
        trial.lexicon.append(LexEntry(form=f, gloss=g, pos="root", count=0))
    sources = sorted({w for _f, (_g, _p, srcs) in proposals.items() for w in srcs})
    res = run_parse(trial, sources, chunk_size=25, chunk_timeout=20, phon_feats=pf)
    parsed = {w for w in sources if res.get(w)}
    return {f: v for f, v in proposals.items() if any(w in parsed for w in v[2])}


def cotrain(pair: str, *, cycles: int = 6, sample: int = 500, gate: float = GATE,
            words: list[str] | None = None, start: LangModel | None = None, pivot: str = "en",
            strip_affixes: bool = True, amb_cap: float = 8.0,
            verify_roundtrip: bool = False, reuse_table: bool = False, verbose: bool = True) -> dict:
    """Run the co-training loop. Returns {history, model, added, secs}. Guarded: a cycle's roots are kept
    only if coverage RISES and mean parse ambiguity stays <= `amb_cap`. Stops at the fixpoint.
    Switches (for ablation):
      strip_affixes   (default on)  propose the affix-stripped ROOT (generalises across inflected forms).
      verify_roundtrip(a, off)      keep a root only if it lets HC re-parse a source word (correctness gate).
      reuse_table     (c, off)      align THOT ONCE and reuse the table every cycle (warm/cheap) instead of
                                    re-aligning on each cycle's new segmentation (the full mutual loop)."""
    import time
    from induce.tdd import _load_prior_model, load_freqs
    from engine.hc import run_parse
    from gold.phonology_gold import phon_feats

    model = start or _load_prior_model(pair)
    if model is None:
        return {"error": f"no model for {pair} (run induction first)", "pair": pair}
    pf = phon_feats(pair, model.charset)
    if words is None:
        ranked = [w for w, _ in load_freqs(pair).most_common() if len(w) >= 2]
        words = ranked[:1000]

    history, total_added = [], []
    t0 = time.monotonic()
    cov0, amb0 = _coverage(model, words, pf)
    table = None
    if verbose:
        print(f"[cotrain {pair}] start: coverage={cov0:.4f} amb={amb0:.2f} roots={len(model.lexicon)} "
              f"affixes={len(model.affixes)} [strip={strip_affixes} roundtrip={verify_roundtrip} "
              f"reuse_table={reuse_table}]", flush=True)

    for k in range(1, cycles + 1):
        # HC: find the gap on the current model
        res = run_parse(model, words, chunk_size=25, chunk_timeout=20, phon_feats=pf)
        unparsed = [w for w in words if not res.get(w)]
        # THOT over the current HC segmentation — (c) reuse the first table if reuse_table, else re-align
        if table is None or not reuse_table:
            table = _align_table(pair, model, sample)
        known = {e.form for e in model.lexicon}
        pre = [a.form for a in model.affixes if a.kind == "prefix"] if strip_affixes else None
        suf = [a.form for a in model.affixes if a.kind == "suffix"] if strip_affixes else None
        proposals = propose_roots(unparsed, table, pivot=pivot, gate=gate, known_forms=known,
                                  prefixes=pre, suffixes=suf)
        n_proposed = len(proposals)
        if verify_roundtrip and proposals:                    # (a) correctness gate
            proposals = _roundtrip_keep(model, proposals, pf)
        if not proposals:
            if verbose:
                print(f"[cotrain {pair}] cycle {k}: no confident proposals — fixpoint.", flush=True)
            break
        # apply, then coverage+ambiguity guard
        trial = _clone(model)
        for f, (g, _p, _s) in proposals.items():
            trial.lexicon.append(LexEntry(form=f, gloss=g, pos="root", count=0))
        cov1, amb1 = _coverage(trial, words, pf)
        rose = cov1 > cov0 + 1e-9
        within_amb = amb1 <= amb_cap
        kept = rose and within_amb
        row = {"cycle": k, "unparsed": len(unparsed), "proposed": n_proposed, "proposals": len(proposals),
               "cov_before": round(cov0, 4), "cov_after": round(cov1, 4),
               "delta": round(cov1 - cov0, 4), "amb": round(amb1, 2), "kept": kept}
        history.append(row)
        if verbose:
            rt = f" roundtrip_kept={len(proposals)}/{n_proposed}" if verify_roundtrip else ""
            print(f"[cotrain {pair}] cycle {k}: unparsed={len(unparsed)} proposals={len(proposals)}{rt} "
                  f"cov {cov0:.4f}->{cov1:.4f} (d{cov1-cov0:+.4f}) amb={amb1:.2f} kept={kept}", flush=True)
        if not kept:
            why = "no coverage gain" if not rose else f"ambiguity {amb1:.2f} > cap {amb_cap}"
            if verbose:
                print(f"[cotrain {pair}] cycle {k}: {why} — stop (guard).", flush=True)
            break
        model, cov0 = trial, cov1
        total_added.extend({"form": f, "gloss": g, "prob": p} for f, (g, p, _s) in proposals.items())

    return {"pair": pair, "cycles_run": len(history), "history": history, "final_coverage": cov0,
            "roots_added": len(total_added), "added": total_added, "model": model,
            "secs": round(time.monotonic() - t0, 1)}


def _clone(model: LangModel) -> LangModel:
    import copy
    return copy.deepcopy(model)


def save_model(pair: str, model: LangModel) -> str:
    """Persist the enriched model back to out/<pair>_model.json in the tdd format, so the next accumulate
    round resumes from the cotrain-augmented grammar (the integration seam for switch b)."""
    import json
    out = Path(__file__).resolve().parent / "out" / f"{pair}_model.json"
    out.write_text(json.dumps({
        "pair": pair,
        "roots": [{"form": e.form, "gloss": e.gloss, "pos": e.pos, "count": e.count} for e in model.lexicon],
        "affixes": [{"form": a.form, "gloss": a.gloss, "kind": a.kind, "slot_ord": a.slot_ord,
                     "req_pos": a.req_pos, "count": a.count} for a in model.affixes],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)


def emit_deltas(pair: str, added: list[dict]) -> int:
    """Route the THOT-glossed induced roots into the confidence store (low/med by alignment prob)."""
    from review.deltas.store import DeltaStore
    path = _RESEARCH / "deltas" / "store" / f"{pair}.deltas.jsonl"
    store = DeltaStore.load(path)
    ops = [{"op": "lexical.entry.create", "entry": f"entry:{pair}:{a['form']}",
            "lexeme": a["form"], "gloss": a["gloss"], "confidence": float(a["prob"]),
            "provenance": {"source": "cotrain-thot-hc", "prob": a["prob"]}}
           for a in added]
    n = store.add(ops) if ops else 0
    if ops:
        store.save()
    return n


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="THOT<->HC co-training loop (coverage-guarded).")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--cycles", type=int, default=6)
    ap.add_argument("--sample", type=int, default=500)
    ap.add_argument("--gate", type=float, default=GATE)
    ap.add_argument("--no-strip", action="store_true", help="propose whole unparsed words as roots (no affix strip)")
    ap.add_argument("--amb-cap", type=float, default=8.0, help="stop if mean parse ambiguity exceeds this")
    ap.add_argument("--roundtrip", action="store_true", help="(a) keep a root only if HC re-parses a source word")
    ap.add_argument("--reuse-table", action="store_true", help="(c) align THOT once and reuse (warm) vs re-align each cycle")
    ap.add_argument("--emit", action="store_true", help="route induced roots into the delta store")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    r = cotrain(a.pair, cycles=a.cycles, sample=a.sample, gate=a.gate, strip_affixes=not a.no_strip,
                amb_cap=a.amb_cap, verify_roundtrip=a.roundtrip, reuse_table=a.reuse_table)
    if r.get("error"):
        print(r["error"]); return 1
    print(f"\n[cotrain {a.pair}] done: {r['cycles_run']} cycles, +{r['roots_added']} roots, "
          f"final coverage={r['final_coverage']:.4f}")
    if a.emit and r["added"]:
        n = emit_deltas(a.pair, r["added"])
        print(f"[cotrain {a.pair}] emitted {n} root deltas to the store.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
