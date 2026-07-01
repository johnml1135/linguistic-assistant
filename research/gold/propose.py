"""Gemma raises the high-confidence lexical layer — and defers the rest to a human.

Runs the model's sense assessment over the aligner's ranked candidates, then ROUTES by a high-precision
gate so it never proposes wrong things:

  ACCEPT  — model is high-confidence AND agrees with the statistical aligner (two independent signals
            concur). These become high-confidence lexical data; where the existing gold gloss is junk/meta
            (yo→"ego/freud", son→the music genre, los→∅) this CORRECTS it — the eBible beats the gold.
  DEFER   — anything else (model unsure, model⊥aligner, function word): handed to a user, not guessed.

Two concurring signals (a generative model + a statistical aligner) make the ACCEPT tier safe without a
dictionary; disagreement is exactly the signal to ask a human. Writes `gemma_proposals.jsonl` per pair.

Run: `uv run python golden/reference/propose.py --pair spa --endpoint local --sample 120`
(`local` = a MAINLINE llama.cpp build for thinking models — NOT ik_llama.cpp, which can't emit Gemma-4
thinking; or `--endpoint opus` for the frontier checker when ANTHROPIC_API_KEY is set.)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from gold.compile import PAIR_DIR  # noqa: E402
from gold.goldio import FROZEN, load_gold  # noqa: E402
from gold.hc_coverage import _scripture_freqs  # noqa: E402
from gold.morphology import is_meta_sense  # noqa: E402
from gold.sense_pick import assess  # noqa: E402


def _toks(s: str) -> set[str]:
    return {t for t in re.split(r"[^a-záéíóúñü]+", (s or "").lower()) if len(t) > 1}


def _apply_accepted(pair: str, accepted: list[dict]) -> dict:
    """Fold the high-confidence ACCEPT tier into the gold's lexicon.jsonl — fill a missing gloss or
    replace a junk/meta one (never overwrite a good existing gloss). Tagged gloss_source='gemma+aligner'
    so corpus-model glosses stay distinguishable from Wiktionary. This is what makes golden better."""
    frozen = FROZEN / pair
    lex_path = frozen / "lexicon.jsonl"
    entries = [json.loads(line) for line in lex_path.read_text(encoding="utf-8").splitlines() if line]
    by_word = {e["word"]: e for e in entries}
    wf_lemma = {w["surface"]: w["lemma"] for w in load_gold(pair).get("wordforms", [])}
    updated = added = 0
    for rec in accepted:
        gl = rec.get("gloss")
        if not gl:
            continue
        lemma = wf_lemma.get(rec["word"], rec["word"])
        e = by_word.get(lemma)
        if e:
            cur = (e.get("senses") or [None])[0]
            if cur is None or is_meta_sense(cur):     # fill/fix only — keep good existing glosses
                e["senses"] = [gl] + [s for s in (e.get("senses") or []) if s != gl]
                e["gloss_source"] = "gemma+aligner"
                updated += 1
        else:                                          # a word no lexeme covered → add it
            ne = {"word": lemma, "pos": rec.get("pos") or "Unknown", "pos_all": [], "senses": [gl],
                  "homograph": False, "in_scripture": True, "inflection_class": None, "stem": lemma,
                  "irregular": [], "gloss_source": "gemma+aligner"}
            entries.append(ne)
            by_word[lemma] = ne
            added += 1
    with lex_path.open("w", encoding="utf-8") as f:
        for e in sorted(entries, key=lambda x: x["word"]):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return {"updated": updated, "added": added}


def propose(pair: str, *, endpoint: str, sample: int = 120, backend: str = "eflomal", apply: bool = False,
            target: str = "frequent") -> dict:
    gold = load_gold(pair)
    gglo = gold.get("glosses", {})
    wf_lemma = {w["surface"]: w["lemma"] for w in gold.get("wordforms", [])}
    freqs = _scripture_freqs(pair)
    ranked = [w for w, _ in freqs.most_common() if w.isalpha() and len(w) > 1]
    if target == "needy":
        # target the words whose lemma has NO gloss or a junk/meta one — every accept then RAISES the gold
        words = [w for w in ranked if (lambda c: c is None or is_meta_sense(c))(gglo.get(wf_lemma.get(w, w)))][:sample]
    else:
        words = ranked[:sample]              # frequent (mostly already glossed) — for precision demos
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
    applied = _apply_accepted(pair, accepted) if apply else {"updated": 0, "added": 0}
    return {"pair": pair, "endpoint": endpoint, "assessed": len([w for w in words if w in a]),
            "accepted": len(accepted), "deferred": len(deferred),
            "raised_gold": sum(1 for r in accepted if r["raises_gold"]), "applied": applied,
            "accept_examples": accepted[:10]}


def propose_morph(pair: str, *, endpoint: str, top: int = 14, k: int = 5, backend: str = "eflomal") -> dict:
    """Gemma names AFFIX FUNCTIONS from base→derived evidence, same accept/defer gate. The MORPHOLOGY
    half: high-confidence affix labels are raised; ambiguous affixes defer to a user."""
    from align.aligner import align as align_corpus
    from propose.harness import build_client
    from propose.harness.base import Message
    from gold.align_gloss import _verses
    from gold.inflection import canon
    skill = (_THIS.parents[1] / "skills" / "affix_function.md").read_text(encoding="utf-8")
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


def propose_morph_seg(pair: str, *, endpoint: str, top: int = 16, k: int = 5, backend: str = "eflomal") -> dict:
    """MORPHOLOGY for languages with no UniMorph: Gemma names the functions of UNSUPERVISED-segmented
    affixes (discovered from eBible) from base→derived evidence, same accept/defer gate. This is how the
    thin languages (tgl/swh) get morphology — no dictionary, alignment+segmentation+model only."""
    from collections import defaultdict
    from align.aligner import align as align_corpus
    from propose.harness import build_client
    from propose.harness.base import Message
    from gold.align_gloss import _verses
    from gold.segment import segment
    skill = (_THIS.parents[1] / "skills" / "affix_function.md").read_text(encoding="utf-8")
    affixes, seg, freq = segment(pair)
    gt, _ = align_corpus([(s, t) for s, t in _verses(pair)], backend=backend, allow_cooccur_fallback=False)
    en = lambda w: (gt.best(w).source_word if gt.best(w) else "?")  # noqa: E731

    # clean minimal pairs straight from the affix inventory: (base, base+affix) where BOTH are free words
    # and the base is real (≥4 chars, frequent) — base→derived differs by exactly the affix.
    words = {w for w in freq if len(w) >= 4 and freq[w] >= 3}
    ex: dict[tuple, list] = defaultdict(list)
    for a in (x for x in affixes["suffix"] if len(x) >= 2):
        for base in words:
            if base + a in freq:
                ex[("suffix", a)].append((base, base + a))
    for a in (x for x in affixes["prefix"] if len(x) >= 2):
        for base in words:
            if a + base in freq:
                ex[("prefix", a)].append((base, a + base))
    client = build_client(endpoint)
    accepted = deferred = 0
    rows = []
    for (kind, af), pairs in sorted(ex.items(), key=lambda kv: -len(kv[1]))[:top]:
        good = [(st, w) for st, w in pairs if en(st) != "?" and en(w) != "?" and en(st) != en(w)][:k]
        if len(good) < 2:
            continue
        shown = "-" + af if kind == "suffix" else af + "-"
        body = "\n".join(f"  - {st} ({en(st)}) → {w} ({en(w)})" for st, w in good)
        res = client.complete([Message("system", skill),
                               Message("user", f"Affix: {shown} ({kind})\nBase → derived pairs:\n{body}\nReturn the JSON.")])
        try:
            p = json.loads(res.text[res.text.find("{"):res.text.rfind("}") + 1])
        except Exception:
            p = {"confidence": "low"}
        hi = p.get("confidence") == "high"
        accepted += hi
        deferred += not hi
        rows.append({"affix": shown, "kind": kind, "n_stems": affixes[kind].get(af),
                     "function": p.get("function"), "feature": p.get("feature") or {},
                     "conf": p.get("confidence"), "examples": [f"{st}→{w}" for st, w in good[:3]]})
    out = FROZEN / pair / "gemma_affix_proposals.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for rec in rows:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"pair": pair, "assessed": len(rows), "accepted": accepted, "deferred": deferred, "examples": rows[:12]}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--endpoint", default="local")
    ap.add_argument("--mode", choices=["lexical", "morph"], default="lexical")
    ap.add_argument("--apply", action="store_true", help="fold accepted glosses into the gold (make golden better)")
    ap.add_argument("--target", choices=["frequent", "needy"], default="frequent",
                    help="needy = words missing/junk gloss (maximises gold improvement); frequent = precision demo")
    ap.add_argument("--sample", type=int, default=120)
    args = ap.parse_args(argv)
    if args.mode == "morph":
        n_classes = len(load_gold(args.pair).get("inflection_classes", []))
        if n_classes >= 3:                            # UniMorph-seeded classes exist (spa/ind)
            s = propose_morph(args.pair, endpoint=args.endpoint)
            print(f"[{args.pair}] Gemma AFFIX-FUNCTION (UniMorph classes) over {s['assessed']} affixes:")
            print(f"  ACCEPT (high-conf): {s['accepted']}  precision vs gold cell {s['precision_high']}   "
                  f"DEFER: {s['deferred']}")
            for r in s["examples"]:
                print(f"    {'✓' if r['hit'] else '·'} -{r['affix']:6} → {str(r['function'])[:22]:22} "
                      f"[{r['conf']}]  gold:{r['gold_cell'][:26]}")
        else:                                          # no UniMorph → unsupervised segmentation (tgl/swh)
            s = propose_morph_seg(args.pair, endpoint=args.endpoint)
            print(f"[{args.pair}] Gemma AFFIX-FUNCTION (UNSUPERVISED segmentation) over {s['assessed']} discovered affixes:")
            print(f"  ACCEPT (high-conf): {s['accepted']}   DEFER to user: {s['deferred']}")
            for r in s["examples"]:
                print(f"    {r['affix']:7} ({r['kind']:6}, {r['n_stems']} stems) → {str(r['function'])[:24]:24} "
                      f"[{r['conf']}]  e.g. {r['examples'][:2]}")
        return 0
    s = propose(args.pair, endpoint=args.endpoint, sample=args.sample, apply=args.apply, target=args.target)
    print(f"[{args.pair}] Gemma sense proposals via '{s['endpoint']}' over {s['assessed']} frequent words:")
    print(f"  ACCEPT (high-conf ∩ aligner-agree): {s['accepted']}  "
          f"(of which {s['raised_gold']} RAISE the gold — fill a missing or fix a junk/meta gloss)")
    print(f"  DEFER to user: {s['deferred']}  ← never a confident guess; a human/speaker resolves these")
    if args.apply:
        print(f"  APPLIED to gold: {s['applied']['updated']} glosses fixed/filled, {s['applied']['added']} new entries")
    print("  sample accepted (word → gloss | replacing gold):")
    for r in s["accept_examples"]:
        print(f"    {r['word']:12} → {str(r['gloss'])[:24]:24} | gold was: {str(r['current_gold'])[:34]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
