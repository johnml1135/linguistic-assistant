"""Quantitative + qualitative evaluation of the LLM (Gemma) layer of the deferral pipeline.

The question the user posed: *did it propose the right things, and did it defer the right ones?* We grade
the model's `resolve_or_defer` decision against two ground-truthed sets:

  RESOLVABLE — real gold words with a known gloss, presented WITH a confident pivot gloss (simulating a
               good aligner). The model SHOULD resolve, and its proposed gloss should match the truth.
               → measures "found the right things" (resolve-rate) + correctness (gloss match).
  DEFER      — isolated non-words / hapax with NO pivot and no near lemma. The model SHOULD defer.
               → measures "deferred the right ones" (defer-rate) + the dangerous false-confident rate.

Plus a small SAMPLE of the (ungradable, subjective) generated prose — context_md and a rephrased speaker
question — printed for human inspection. Requires a live endpoint; prints a clear message otherwise.
"""

from __future__ import annotations

import re

from golden.reference.goldio import load_gold

from . import counterfactual as CF
from . import llm
from . import profile as P
from .taxonomy import _nearest_lemma

_TOK = re.compile(r"[^0-9a-záéíóúñü]+")
# deterministic pseudo-nonwords (no RNG — reproducible); not Spanish/Indonesian/etc. words
_ISOLATES = ["zqxvor", "blethurn", "vimquap", "drazzol", "frintew", "klozvan", "myrtokk", "wuxneld",
             "phrabik", "tsernquo", "gloznit", "varkuum"]


def _toks(s: str) -> set[str]:
    return {t for t in _TOK.split((s or "").lower()) if len(t) > 1}


def _resolvable_set(pair: str, gold: dict, n: int) -> list[dict]:
    """Frequent gold words that HAVE a real gloss — presented with that gloss as the pivot (a confident
    aligner). The model should resolve; correctness = its gloss overlaps the true gloss."""
    freqs = CF._freqs(pair)
    glosses = gold.get("glosses", {})
    lemmas = gold.get("lemmas", [])
    ranked = [w for w, _ in freqs.most_common() if w.isalpha() and len(w) > 2 and glosses.get(w)]
    out = []
    for w in ranked[: n * 3]:
        g = glosses[w]
        if not g or any(x in g.lower() for x in ("initialism", "surname", "given name", "roman numeral")):
            continue
        out.append({"pair": pair, "language": P.LANG_NAME.get(pair, pair) if hasattr(P, "LANG_NAME") else pair,
                    "form": w, "pivot_gloss": g, "near_lemma": _nearest_lemma(w, lemmas),
                    "context": "", "truth_gloss": g})
        if len(out) >= n:
            break
    return out


def _defer_set(pair: str, n: int) -> list[dict]:
    """Isolated pseudo-words with no pivot gloss and no near lemma — the model should defer."""
    return [{"pair": pair, "language": pair, "form": w, "pivot_gloss": "?", "near_lemma": None,
             "context": ""} for w in _ISOLATES[:n]]


def run_eval(pair: str, *, endpoint: str = "ik_llama", n_resolvable: int = 12, n_defer: int = 8,
             samples: int = 3) -> dict:
    """Grade Gemma's resolve/defer decisions; return metrics + a few subjective prose samples."""
    gold = load_gold(pair)
    prof = P.load(pair)
    psum = f"morph_type={prof.morph_type}; allowed_affix={sorted(prof.allowed_affix_kinds())}"

    resolvable = _resolvable_set(pair, gold, n_resolvable)
    deferr = _defer_set(pair, n_defer)

    # RESOLVABLE — should resolve, with a correct gloss
    res_resolved = res_gloss_ok = 0
    res_rows = []
    for rec in resolvable:
        d = llm.resolve_or_defer(rec, endpoint=endpoint, profile_summary=psum)
        resolved = d["decision"] == "resolve"
        res_resolved += resolved
        edit = d.get("edit") or {}
        prop_gloss = edit.get("params", {}).get("gloss", "") if resolved else ""
        ok = resolved and (bool(_toks(prop_gloss) & _toks(rec["truth_gloss"]))
                           or edit.get("kind") == "add_allomorph")
        res_gloss_ok += ok
        res_rows.append({"form": rec["form"], "truth": rec["truth_gloss"], "decision": d["decision"],
                         "proposed": prop_gloss or edit.get("kind", ""), "correct": bool(ok)})

    # DEFER — should defer; a high-confidence resolve is the dangerous failure
    def_deferred = def_false_confident = 0
    def_rows = []
    for rec in deferr:
        d = llm.resolve_or_defer(rec, endpoint=endpoint, profile_summary=psum)
        deferred = d["decision"] == "defer"
        def_deferred += deferred
        fc = (not deferred) and d.get("confidence") == "high"
        def_false_confident += fc
        def_rows.append({"form": rec["form"], "decision": d["decision"], "conf": d.get("confidence")})

    nr, nd = len(resolvable), len(deferr)
    metrics = {
        "pair": pair, "endpoint": endpoint, "n_resolvable": nr, "n_defer": nd,
        # "found the right things"
        "resolve_rate": round(res_resolved / nr, 3) if nr else None,
        "gloss_correct_rate": round(res_gloss_ok / nr, 3) if nr else None,
        "gloss_precision_of_resolved": round(res_gloss_ok / res_resolved, 3) if res_resolved else None,
        # "deferred the right ones"
        "defer_rate_on_unresolvable": round(def_deferred / nd, 3) if nd else None,
        "false_confident_rate": round(def_false_confident / nd, 3) if nd else None,
        "resolvable_examples": res_rows[:6], "defer_examples": def_rows[:6],
    }
    return metrics


def sample_prose(pair: str, *, endpoint: str = "ik_llama") -> dict:
    """The subjective, ungradable outputs — a sample enriched ticket's prose + a rephrased question."""
    from . import build, enrich
    from .llm import phrase_question
    gold = load_gold(pair)
    freqs = CF._freqs(pair)
    word = next((w for w, _ in freqs.most_common() if w.isalpha() and len(w) > 3
                 and not gold.get("glosses", {}).get(w)), "amare")
    rec = {"word": word, "gloss": "", "aligner_top1": "", "conf": "low", "decision": "defer"}
    t = build.build_ticket(pair, rec, gold=gold, with_counterfactuals=False)
    enr = enrich.enrich(t, endpoint=endpoint)
    q = phrase_question(t, t.presentation_options[0].id, endpoint=endpoint) if t.presentation_options else None
    return {"word": word, "enrich": enr, "context_md_tail": t.context_md[-400:],
            "llm_hypotheses": [h.description for h in t.hypotheses if h.source == "llm"],
            "rephrased_question": q}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", default="spa")
    ap.add_argument("--endpoint", default="ik_llama")
    ap.add_argument("--n-resolvable", type=int, default=12)
    ap.add_argument("--n-defer", type=int, default=8)
    ap.add_argument("--prose", action="store_true", help="also print subjective prose samples")
    args = ap.parse_args(argv)
    m = run_eval(args.pair, endpoint=args.endpoint, n_resolvable=args.n_resolvable, n_defer=args.n_defer)
    print(f"\n=== Gemma deferral-decision eval [{m['pair']}] via {m['endpoint']} ===")
    print(f"  FOUND THE RIGHT THINGS (resolvable, n={m['n_resolvable']}):")
    print(f"    resolve_rate            {m['resolve_rate']}   (should be high — it has the evidence)")
    print(f"    gloss_correct_rate      {m['gloss_correct_rate']}   (right meaning, over all resolvable)")
    print(f"    gloss_precision         {m['gloss_precision_of_resolved']}   (right meaning | it resolved)")
    print(f"  DEFERRED THE RIGHT ONES (unresolvable, n={m['n_defer']}):")
    print(f"    defer_rate              {m['defer_rate_on_unresolvable']}   (should be high)")
    print(f"    false_confident_rate    {m['false_confident_rate']}   (should be ~0 — dangerous if not)")
    print("  sample resolvable decisions:")
    for r in m["resolvable_examples"]:
        print(f"    {'OK ' if r['correct'] else '   '} {r['form']:14} truth='{r['truth'][:24]}' "
              f"-> {r['decision']}:{str(r['proposed'])[:24]}")
    print("  sample defer decisions:")
    for r in m["defer_examples"]:
        print(f"    {'OK ' if r['decision']=='defer' else 'XX '} {r['form']:14} -> {r['decision']} ({r['conf']})")
    if args.prose:
        s = sample_prose(args.pair, endpoint=args.endpoint)
        print(f"\n  --- subjective prose sample (word '{s['word']}') ---")
        print(f"    enrich: {s['enrich']}")
        print(f"    LLM hypotheses: {s['llm_hypotheses']}")
        print(f"    rephrased question: {s['rephrased_question']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
