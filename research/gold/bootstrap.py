"""Reconstruct the golden set from eBible ALONE (no Wiktionary/UniMorph/UD) — and score it against the
verified gold. This is the TDD metric for the real goal: "how much of the gold can be rebuilt from the
parallel corpus (+ audio), the way it must be for an unknown language?"

Baseline pipeline (dictionary inputs OFF):
  glosses  ← word-alignment to English (`align_gloss`, the source of truth)
  POS      ← project the aligned English word's POS (`cycle.pos.pos_of` → LibLCM)
  (morphology/classes/features ← need unsupervised SEGMENTATION + audio→phonology — the next scaffolds;
   reported here as the gap, scored 0 until built.)

Then score each reconstructed part against `golden_sets/<pair>/` (built from rich resources):
  gloss accuracy, POS accuracy, and lexicon/coverage. Run: `python golden/reference/bootstrap.py --pair spa`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[1]))

from align.aligner import align as align_corpus  # noqa: E402
from align.backends import eflomal_available as _eflomal_available  # noqa: E402

from gold.align_gloss import _verses  # noqa: E402
from gold.compile import PAIR_DIR  # noqa: E402
from gold.goldio import load_gold  # noqa: E402

# Pivot language of the CALIBRATION pairs (their bibles are eng-engwebp). English is fine for the golden
# set; it is NOT assumed in the generic path — the aligner is token↔token and Gemma's assessment is
# multilingual, so a future non-English-pivot set just sets a different pivot and reuses everything.
PIVOT_LANG = "en"


def reconstruct(pair: str, *, backend: str = "eflomal", endpoint: str | None = None,
                pos_baseline: bool = False, words: list[str] | None = None, sample: int = 400):
    """eBible-only reconstruction. The aligner supplies ranked candidate glosses (language-agnostic); the
    ASSESSMENT (which gloss, what POS) is the model's job (`--endpoint` = Gemma/…), reading the word's
    verses + candidates. `pos_baseline` projects POS from the English pivot via `cycle.pos.pos_of` — a
    cheap CALIBRATION-ONLY baseline (valid only when the pivot is English), never the generic path.
    THOT required; no silent co-occurrence fallback."""
    if backend == "eflomal" and not _eflomal_available():
        raise RuntimeError(
            "THOT Eflomal aligner unavailable — refusing to silently degrade to co-occurrence. "
            "Run under `uv run python …` (install: `uv sync --extra align`); or pass --backend cooccur explicitly.")
    if endpoint:
        from gold.sense_pick import assess
        return assess(pair, endpoint=endpoint, words=words, sample=sample, backend=backend), f"eflomal+assess:{endpoint}"
    verses = _verses(pair)
    gt, used = align_corpus([(src, tgt) for src, tgt in verses], backend=backend, allow_cooccur_fallback=False)
    _pos_of = None
    if pos_baseline:
        import liblcm
        from induce.pos import pos_of
        _pos_of = lambda g: liblcm.pos_from_cycle(pos_of(g))  # noqa: E731
        used += "+english-pos-baseline"
    out: dict[str, dict] = {}
    for w, cands in gt.table.items():
        if not cands:
            continue
        cg = cands[0]
        conf = "high" if cg.prob >= 0.5 and cg.count >= 2 else "medium" if cg.prob >= 0.25 else "low"
        out[w] = {"gloss": cg.source_word, "conf": conf, "prob": round(cg.prob, 3),
                  "pos": _pos_of(cg.source_word) if _pos_of else None}
    return out, used


def score(pair: str, *, backend: str = "eflomal", endpoint: str | None = None,
          pos_baseline: bool = False, sample: int = 400) -> dict:
    gold = load_gold(pair)
    gpos, gglo = gold.get("pos", {}), gold.get("glosses", {})
    # when a model assesses, target the most FREQUENT gold lemmas (the words that matter + are actually
    # aligned), not alphabetical-first ones that never appear in the aligner table
    words = None
    if endpoint:
        from gold.hc_coverage import _scripture_freqs
        freqs = _scripture_freqs(pair)
        words = sorted(gglo, key=lambda lm: -freqs.get(lm, 0))[:sample]
    recon, used = reconstruct(pair, backend=backend, endpoint=endpoint, pos_baseline=pos_baseline,
                              words=words, sample=sample)

    def toks(s: str) -> set[str]:
        return {t.strip(".,;:()") for t in str(s).lower().split()}

    # gold sense tokens = ALL senses of a lemma (not just the first — Wiktionary's first sense is sometimes
    # junk, e.g. pan→"initialism of PAN", so matching only it unfairly penalises a correct alignment).
    gsenses = gold.get("senses", {})
    gold_tok = {lm: set().union(*(toks(s) for s in (gsenses.get(lm, {}).get("senses") or [gglo.get(lm, "")])))
                for lm in gglo}

    # Goal-aligned scoring: a model should PROPOSE high-confidence correct glosses and DEFER (gloss=None)
    # rather than guess wrong. So we separate correct / wrong / deferred, and report precision@high
    # (of high-conf proposals, how many are right — want →1) and the wrong-rate (want →0).
    import re as _re
    g_eval = g_ok = proposed = correct = wrong = deferred = hi_prop = hi_ok = acc_prop = acc_ok = 0
    for lm in gglo:
        if lm not in recon:
            continue
        g_eval += 1
        gl = (recon[lm].get("gloss") or "").lower()
        if not gl:
            deferred += 1
            continue
        proposed += 1
        # credit if ANY content token of the model's (possibly multi-word) gloss matches a gold sense
        gl_toks = {t for t in _re.split(r"[^a-záéíóúñü]+", gl) if len(t) > 1}
        hit = bool(gl_toks & gold_tok.get(lm, set())) or gl in gold_tok.get(lm, set()) or gl == lm
        correct += hit
        wrong += not hit
        g_ok += hit
        if recon[lm].get("conf") == "high":
            hi_prop += 1
            hi_ok += hit
        # ACCEPTANCE GATE: auto-accept only when the model is high-conf AND agrees with the aligner
        # (the model's gloss shares a token with the aligner's top-1) — everything else DEFERS to a user.
        a1 = (recon[lm].get("aligner_top1") or "").lower()
        if recon[lm].get("conf") == "high" and (a1 in gl_toks or a1 == gl):
            acc_prop += 1
            acc_ok += hit
    # POS accuracy: projected POS vs gold POS (on gold lemmas we glossed)
    p_eval = p_ok = 0
    for lm, p in gpos.items():
        if lm in recon and recon[lm].get("pos") and recon[lm]["pos"] != "Unknown":
            p_eval += 1
            if recon[lm]["pos"] == p:
                p_ok += 1
    gold_lemmas = set(gold.get("lemmas", []))
    return {
        "pair": pair, "backend": used, "reconstructed_words": len(recon),
        "gloss": {"evaluated": g_eval, "correct": g_ok, "accuracy": round(g_ok / g_eval, 4) if g_eval else 0.0,
                  "proposed": proposed, "wrong": wrong, "deferred": deferred,
                  "precision": round(correct / proposed, 4) if proposed else 0.0,
                  "wrong_rate": round(wrong / g_eval, 4) if g_eval else 0.0,
                  "deferral_rate": round(deferred / g_eval, 4) if g_eval else 0.0},
        "gloss_high_conf": {"evaluated": hi_prop, "correct": hi_ok,
                            "precision": round(hi_ok / hi_prop, 4) if hi_prop else 0.0},
        "gloss_accepted": {"accepted": acc_prop, "correct": acc_ok,
                           "precision": round(acc_ok / acc_prop, 4) if acc_prop else 0.0,
                           "accept_rate": round(acc_prop / g_eval, 4) if g_eval else 0.0,
                           "deferred_to_user": g_eval - acc_prop},
        "pos": {"evaluated": p_eval, "correct": p_ok, "accuracy": round(p_ok / p_eval, 4) if p_eval else 0.0},
        "lemma_coverage": round(len(gold_lemmas & set(recon)) / len(gold_lemmas), 4) if gold_lemmas else 0.0,
        # parts that need the next scaffolds (no segmentation / audio wired into the no-dict path yet)
        "morphology": "not in baseline — needs unsupervised segmentation (scaffold #2)",
        "inflection_classes": "not in baseline — needs paradigms from segmentation",
        "phonology": "not in baseline — needs audio→phonology wiring",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--backend", choices=["eflomal", "cooccur"], default="eflomal",
                    help="eflomal (THOT, required by default — fails if absent, no silent degrade); "
                         "cooccur = explicit weak baseline")
    ap.add_argument("--endpoint", default=None,
                    help="model for the ASSESSMENT (gloss+POS): ollama (Gemma) | vllm (Qwen) | opus | mock. "
                         "Without it, only the raw aligner top-1 gloss is scored (no POS — that's the model's job).")
    ap.add_argument("--pos-baseline", action="store_true",
                    help="project POS from the English pivot (cheap CALIBRATION baseline; English-only)")
    ap.add_argument("--sample", type=int, default=400)
    args = ap.parse_args(argv)
    s = score(args.pair, backend=args.backend, endpoint=args.endpoint,
              pos_baseline=args.pos_baseline, sample=args.sample)
    print(f"[{args.pair}] golden set REBUILT FROM eBible ALONE (no dictionary) — vs the verified gold:")
    print(f"  aligner: {s['backend']}   reconstructed {s['reconstructed_words']} words")
    g = s["gloss"]
    print(f"  GLOSS: accuracy {g['accuracy']} ({g['correct']}/{g['evaluated']})  |  "
          f"precision@high {s['gloss_high_conf']['precision']} ({s['gloss_high_conf']['correct']}/{s['gloss_high_conf']['evaluated']})")
    print(f"         proposed {g['proposed']}, WRONG {g['wrong']} (rate {g['wrong_rate']}), "
          f"DEFERRED {g['deferred']} (rate {g['deferral_rate']})")
    a = s["gloss_accepted"]
    print(f"  ACCEPT GATE (model-high ∩ aligner-agree): precision {a['precision']} ({a['correct']}/{a['accepted']}) "
          f"accept-rate {a['accept_rate']}, {a['deferred_to_user']} deferred to user  ← the deployable high-confidence tier")
    print(f"  POS   accuracy: {s['pos']['accuracy']}  ({s['pos']['correct']}/{s['pos']['evaluated']} gold lemmas)")
    print(f"  gold-lemma coverage: {s['lemma_coverage']}")
    print(f"  morphology / classes / phonology: {s['morphology'].split('—')[0].strip()} (next scaffolds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
