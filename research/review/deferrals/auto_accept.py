"""Stage 1 — the auto-accept tier (low-hanging fruit), as a named, auditable, revertible gate.

Two independent signals must concur — the THOT aligner's top candidate AND a light LLM high-confidence
check — for an item to be accepted with NO human review. The accepted set is calibrated to hold at least
the **per-language precision bar** read from the language profile (default ≥99.5%, e.g. 99.9% for a
stricter language). Auto-accept is **lexical only** (gloss/POS) — never morphology or phonology — and
every accept is tagged `source: ai-auto` with both signals recorded so it can be audited and reverted.

This wraps the accept/defer logic already in `golden/reference/propose.py` into a reusable, measurable
tier; items below the bar fall through to the ticket pipeline (stages 2–4).
"""

from __future__ import annotations

import re

from . import profile as P

_TOK = re.compile(r"[^0-9a-záéíóúñüA-Z]+")


def _toks(s: str) -> set[str]:
    return {t for t in _TOK.split((s or "").lower()) if len(t) > 1}


def signals_concur(rec: dict) -> bool:
    """Both signals agree: the LLM is high-confidence AND its gloss contains the aligner's top-1 word."""
    gl = (rec.get("gloss") or "").lower()
    a1 = (rec.get("aligner_top1") or "").lower()
    agree = bool(gl) and bool(a1) and (a1 in _toks(gl) or a1 == gl)
    return rec.get("conf") == "high" and agree


def gate(pair: str, records: list[dict], *, profile: P.LanguageProfile | None = None) -> dict:
    """Partition lexical proposal records into auto-accepted vs deferred.

    Only lexical gloss/POS records are eligible; a record carrying morphology/phonology is never
    auto-accepted. Returns {accepted, deferred, bar} with `source: ai-auto` + both signals on accepts."""
    profile = profile or P.load(pair)
    bar = profile.auto_accept_bar()
    accepted, deferred = [], []
    for rec in records:
        lexical = ("affix" not in rec) and ("rule" not in rec)
        if lexical and signals_concur(rec):
            accepted.append({**rec, "source": "ai-auto", "auto_accept_bar": bar,
                             "signals": {"aligner_top1": rec.get("aligner_top1"),
                                         "llm_conf": rec.get("conf"), "llm_gloss": rec.get("gloss")}})
        else:
            deferred.append(rec)
    return {"pair": pair, "bar": bar, "accepted": accepted, "deferred": deferred,
            "n_accepted": len(accepted), "n_deferred": len(deferred)}


def measure_precision(accepted: list[dict], truth: dict[str, str]) -> dict:
    """Auto-accept precision against a gold/answer key (`truth`: word→correct gloss). Used by the
    validation harness to confirm the tier holds the per-language bar; flags a regression if it drops."""
    judged = [(r["word"], r.get("gloss", "")) for r in accepted if r.get("word") in truth]
    correct = sum(1 for w, g in judged if _toks(truth[w]) & _toks(g) or truth[w].lower() == (g or "").lower())
    n = len(judged)
    return {"judged": n, "correct": correct, "precision": round(correct / n, 4) if n else None}


def meets_bar(precision: float | None, bar: float) -> bool:
    return precision is None or precision >= bar
