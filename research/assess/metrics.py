"""Pure-math implementations of the `assess-grammar-metrics` measures.

Every function operates on plain data structures (no `hc`, no I/O) so the formulas are unit-testable
offline. The hc-driving and LibLCM-reading adapters live in `hc_adapter.py` / `inventory.py`.

Data conventions:
- ``parses``: ``dict[str, list[tuple[str, ...]]]`` — wordform -> list of distinct analyses, each an
  ordered tuple of glosses (the gloss *line*; reliable even when HC corrupts morph forms — see
  `golden/hc.py`). Distinctness is the caller's responsibility (dedup analyses).
- ``token_counts``: ``dict[str, int]`` — wordform -> corpus token frequency (default 1 each).
- ``gold``: ``dict[str, tuple[str, ...]]`` — wordform -> the gold gloss line (the answer key).
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

GlossLine = tuple[str, ...]
Parses = dict[str, list[GlossLine]]


# ---------------------------------------------------------------------------------- coverage / ambiguity

def coverage(parses: Parses, token_counts: dict[str, int] | None = None) -> dict:
    """`coverage_type` and `coverage_token` per the spec. Never report either alone (caller bundles)."""
    W = list(parses)
    if not W:
        return {"coverage_type": 0.0, "coverage_token": 0.0, "n_types": 0, "n_parsed_types": 0}
    tc = token_counts or {w: 1 for w in W}
    parsed = [w for w in W if parses[w]]
    cov_type = len(parsed) / len(W)
    tot_tok = sum(tc.get(w, 0) for w in W) or 1
    cov_tok = sum(tc.get(w, 0) for w in parsed) / tot_tok
    return {
        "coverage_type": round(cov_type, 6),
        "coverage_token": round(cov_tok, 6),
        "n_types": len(W),
        "n_parsed_types": len(parsed),
    }


def spurious_ambiguity(parses: Parses) -> dict:
    """`mean_analyses`, `ambiguity_rate`, `average_parse_base` over PARSED words. Lower is better."""
    parsed = [w for w in parses if parses[w]]
    if not parsed:
        return {"mean_analyses": 0.0, "ambiguity_rate": 0.0, "average_parse_base": 0.0, "n_parsed": 0}
    counts = [len(parses[w]) for w in parsed]
    mean = sum(counts) / len(counts)
    rate = sum(1 for c in counts if c > 1) / len(counts)
    apb = math.exp(sum(math.log(c) for c in counts) / len(counts))  # geometric mean (Carroll & Briscoe 1998)
    return {
        "mean_analyses": round(mean, 6),
        "ambiguity_rate": round(rate, 6),
        "average_parse_base": round(apb, 6),
        "n_parsed": len(parsed),
    }


# ------------------------------------------------------------------------------------- gold round-trip

def gold_roundtrip(parses: Parses, gold: dict[str, GlossLine]) -> dict:
    """Exact-analysis recall: fraction of gold words whose gold gloss line is among HC's analyses.

    This is the reliable, gloss-line correctness used by `golden/hc.py` (HC corrupts morph *forms*,
    so boundary-F1 from HC output is unreliable — use `boundary_prf` only where segmentation is sound).
    """
    if not gold:
        return {"exact_analysis_recall": 0.0, "n_gold": 0}
    hits = sum(1 for w, g in gold.items() if g in set(parses.get(w, [])))
    return {"exact_analysis_recall": round(hits / len(gold), 6), "n_gold": len(gold)}


def boundary_prf(pred_seg: dict[str, list[int]], gold_seg: dict[str, list[int]]) -> dict:
    """SIGMORPHON-2022 boundary precision/recall/F1 over segmentation boundary positions.

    Use only where the predicted segmentation is reliable (e.g. LibLCM analyses, or a parser whose
    morph forms are trustworthy). Each value is a set of integer boundary offsets within the word.
    """
    inter = pred = goldn = 0
    for w in set(pred_seg) | set(gold_seg):
        p, g = set(pred_seg.get(w, [])), set(gold_seg.get(w, []))
        inter += len(p & g)
        pred += len(p)
        goldn += len(g)
    P = inter / pred if pred else 0.0
    R = inter / goldn if goldn else 0.0
    F1 = 2 * P * R / (P + R) if (P + R) else 0.0
    return {"precision": round(P, 6), "recall": round(R, 6), "f1": round(F1, 6)}


def overgeneration(parses: Parses, gold: dict[str, GlossLine]) -> dict:
    """`overgeneration_rate` = spurious analyses / all analyses, over gold words (Batsuren et al. 2022)."""
    total = spurious = 0
    for w, g in gold.items():
        got = parses.get(w, [])
        total += len(got)
        spurious += sum(1 for a in got if a != g)
    return {"overgeneration_rate": round(spurious / total, 6) if total else 0.0, "n_analyses": total}


def non_regression(before: Parses, after: Parses, gold: dict[str, GlossLine]) -> dict:
    """Gate check: no previously-correct word loses its gold analysis or gains a new spurious one."""
    lost, new_spurious = [], []
    for w, g in gold.items():
        b, a = set(before.get(w, [])), set(after.get(w, []))
        if g in b and g not in a:
            lost.append(w)
        # new analyses (other than gold) that weren't there before
        if (a - b) - {g}:
            new_spurious.append(w)
    return {"ok": not lost and not new_spurious, "lost_correct": lost, "new_spurious": new_spurious}


# ------------------------------------------------------------------------------- inventory-derived

def grammar_size(counts: dict[str, int], weights: dict[str, float] | None = None) -> dict:
    """Raw per-type counts (always shown) + a transparent weighted size `S` (SPE/Goldsmith proxy)."""
    w = weights or {k: 1.0 for k in counts}
    S = sum(w.get(k, 1.0) * n for k, n in counts.items())
    return {"counts": dict(sorted(counts.items())), "weights": dict(sorted(w.items())), "weighted_size": round(S, 4)}


def generalization_ratio(n_alternations: int, n_rule_derived: int) -> dict:
    """rule-derived / total morphophonemic alternations. None when there are no alternations (e.g. v1)."""
    if n_alternations <= 0:
        return {"generalization_ratio": None, "reason": "no morphophonemic alternations", "n_alternations": 0}
    return {
        "generalization_ratio": round(n_rule_derived / n_alternations, 6),
        "n_alternations": n_alternations,
        "n_rule_derived": n_rule_derived,
    }


def dead_constructs(parses: Parses, inventory_glosses: Iterable[str]) -> dict:
    """Constructs whose gloss never appears in any analysis (fires = 0). Pruning candidates."""
    used: set[str] = set()
    for analyses in parses.values():
        for a in analyses:
            used.update(a)
    dead = sorted(g for g in set(inventory_glosses) if g not in used)
    return {"dead": dead, "n_dead": len(dead)}


# --------------------------------------------------------------------------------------- productivity

def tolerance_productive(n_items: int, n_exceptions: int) -> dict:
    """Yang (2016) Tolerance Principle: a rule over N items with e exceptions is productive iff e <= N/ln N."""
    if n_items is None or n_items < 2:
        return {"productive": None, "reason": "not-computable (N<2 or undefinable class)", "n_items": n_items}
    threshold = n_items / math.log(n_items)
    return {
        "productive": n_exceptions <= threshold,
        "n_items": n_items,
        "n_exceptions": n_exceptions,
        "threshold": round(threshold, 4),
    }
