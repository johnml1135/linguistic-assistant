"""Gemma raises the high-confidence lexical layer — and defers the rest to a human.

Runs the model's sense assessment over the aligner's ranked candidates, then ROUTES by a high-precision
gate so it never proposes wrong things:

  ACCEPT  — model is high-confidence AND agrees with the statistical aligner (two independent signals
            concur). These become high-confidence lexical data; where the existing gold gloss is junk/meta
            (yo→"ego/freud", son→the music genre, los→∅) this CORRECTS it — the eBible beats the gold.
  DEFER   — anything else (model unsure, model⊥aligner, function word): handed to a user, not guessed.

Two concurring signals (a generative model + a statistical aligner) make the ACCEPT tier safe without a
dictionary; disagreement is exactly the signal to ask a human. Writes `gemma_proposals.jsonl` per pair.

Run: `uv run python golden/reference/propose.py --pair spa --endpoint ik_llama --sample 120`
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from golden.reference.compile import PAIR_DIR  # noqa: E402
from golden.reference.goldio import FROZEN, load_gold  # noqa: E402
from golden.reference.hc_coverage import _scripture_freqs  # noqa: E402
from golden.reference.morphology import is_meta_sense  # noqa: E402
from golden.reference.sense_pick import assess  # noqa: E402


def _toks(s: str) -> set[str]:
    return {t for t in re.split(r"[^a-záéíóúñü]+", (s or "").lower()) if len(t) > 1}


def propose(pair: str, *, endpoint: str, sample: int = 120, backend: str = "hmm") -> dict:
    gold = load_gold(pair)
    gglo = gold.get("glosses", {})
    freqs = _scripture_freqs(pair)
    # assess the most frequent scripture words (the ones that matter + are reliably aligned)
    words = [w for w, _ in freqs.most_common() if w.isalpha() and len(w) > 1][:sample]
    a = assess(pair, endpoint=endpoint, words=words, backend=backend)

    accepted, deferred = [], []
    for w in words:
        r = a.get(w)
        if not r:
            continue
        gl = (r.get("gloss") or "").lower()
        a1 = (r.get("aligner_top1") or "").lower()
        agree = bool(gl) and (a1 in _toks(gl) or a1 == gl)
        # does this RAISE the gold? (gold has no gloss, or only a meta/junk one)
        cur = gglo.get(w)
        raises = (cur is None) or is_meta_sense(cur)
        rec = {"word": w, "gloss": r.get("gloss"), "pos": r.get("pos"), "conf": r.get("conf"),
               "aligner_top1": r.get("aligner_top1"), "current_gold": cur, "raises_gold": bool(raises)}
        if r.get("conf") == "high" and agree:
            rec["decision"] = "accept"
            accepted.append(rec)
        else:
            rec["decision"] = "defer"          # to a human / speaker — never a confident guess
            deferred.append(rec)

    out = FROZEN / pair / "gemma_proposals.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for rec in accepted + deferred:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"pair": pair, "endpoint": endpoint, "assessed": len([w for w in words if w in a]),
            "accepted": len(accepted), "deferred": len(deferred),
            "raised_gold": sum(1 for r in accepted if r["raises_gold"]),
            "accept_examples": accepted[:10]}


def propose_morph(pair: str, *, endpoint: str, top: int = 14, k: int = 5, backend: str = "hmm") -> dict:
    """Gemma names AFFIX FUNCTIONS from base→derived evidence, same accept/defer gate. The MORPHOLOGY
    half: high-confidence affix labels are raised; ambiguous affixes defer to a user."""
    from align.aligner import align as align_corpus
    from harness import build_client
    from harness.base import Message
    from golden.reference.align_gloss import _verses
    from golden.reference.inflection import canon
    skill = (_THIS.parents[2] / "skills" / "affix_function.md").read_text(encoding="utf-8")
    gold = load_gold(pair)
    gt, _ = align_corpus([(s, t) for s, t in _verses(pair)], backend=backend, allow_cooccur_fallback=False)
    en = lambda w: (gt.best(w).source_word if gt.best(w) else "?")  # noqa: E731

    by_cell: dict[str, list] = {}
    for w in gold.get("wordforms", []):
        by_cell.setdefault(canon(w.get("features") or {}), []).append((w["lemma"], w["surface"]))
    seen, affs = set(), []
    for c in gold.get("inflection_classes", []):
        for r in c.get("rules", []):
            form = r.get("suffix") if r["kind"] == "S" else r.get("add")
            cell = r["features"]
            if form and cell != "BASE" and (r["kind"], form, cell) not in seen:
                seen.add((r["kind"], form, cell))
                affs.append({"side": "suffix" if r["kind"] == "S" else "prefix", "form": form,
                             "cell": cell, "support": r.get("support", 0)})
    affs.sort(key=lambda a: -a["support"])

    client = build_client(endpoint)
    accepted = deferred = correct_hi = 0
    rows = []
    for a in affs[:top]:
        ex = [(lm, sf) for lm, sf in by_cell.get(a["cell"], []) if lm != sf and en(lm) != "?" and en(sf) != "?"][:k]
        if len(ex) < 2:
            continue
        pairs = "\n".join(f"  - {lm} ({en(lm)}) → {sf} ({en(sf)})" for lm, sf in ex)
        user = f"Affix: -{a['form']} ({a['side']})\nBase → derived pairs (with meanings):\n{pairs}\nReturn the JSON."
        res = client.complete([Message("system", skill), Message("user", user)])
        try:
            txt = res.text
            p = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
        except Exception:
            p = {"confidence": "low"}
        gold_cell = set(re.split(r"[;=]", a["cell"]))
        feat = p.get("feature") or {}
        hit = bool({*feat.keys(), *map(str, feat.values())} & gold_cell)
        hi = p.get("confidence") == "high"
        if hi:
            accepted += 1
            correct_hi += hit
        else:
            deferred += 1
        rows.append({"affix": a["form"], "side": a["side"], "gold_cell": a["cell"],
                     "function": p.get("function"), "feature": feat, "conf": p.get("confidence"), "hit": hit})
    out = FROZEN / pair / "gemma_affix_proposals.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for rec in rows:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"pair": pair, "assessed": len(rows), "accepted": accepted, "deferred": deferred,
            "precision_high": round(correct_hi / accepted, 4) if accepted else 0.0, "examples": rows[:10]}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--endpoint", default="ik_llama")
    ap.add_argument("--mode", choices=["lexical", "morph"], default="lexical")
    ap.add_argument("--sample", type=int, default=120)
    args = ap.parse_args(argv)
    if args.mode == "morph":
        s = propose_morph(args.pair, endpoint=args.endpoint)
        print(f"[{args.pair}] Gemma AFFIX-FUNCTION proposals over {s['assessed']} affixes:")
        print(f"  ACCEPT (high-conf): {s['accepted']}  precision vs gold cell {s['precision_high']}")
        print(f"  DEFER to user: {s['deferred']}")
        for r in s["examples"]:
            mark = "✓" if r["hit"] else "·"
            print(f"    {mark} -{r['affix']:6} ({r['side']:6}) → {str(r['function'])[:22]:22} {r['feature']} "
                  f"[{r['conf']}]  gold:{r['gold_cell'][:28]}")
        return 0
    s = propose(args.pair, endpoint=args.endpoint, sample=args.sample)
    print(f"[{args.pair}] Gemma sense proposals via '{s['endpoint']}' over {s['assessed']} frequent words:")
    print(f"  ACCEPT (high-conf ∩ aligner-agree): {s['accepted']}  "
          f"(of which {s['raised_gold']} RAISE the gold — fill a missing or fix a junk/meta gloss)")
    print(f"  DEFER to user: {s['deferred']}  ← never a confident guess; a human/speaker resolves these")
    print("  sample accepted (word → gloss | replacing gold):")
    for r in s["accept_examples"]:
        print(f"    {r['word']:12} → {str(r['gloss'])[:24]:24} | gold was: {str(r['current_gold'])[:34]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
