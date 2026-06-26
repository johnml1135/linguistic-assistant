"""Generic feature-affix detector — surface the affixes that the held-out feature-predictor
(`review/affix_function.py`) labels with a given FEATURE FAMILY, as paradigm cells. One mechanism, many
paradigms: possessive/number = {Person, Number, Poss}, mood = {Mood}, etc. (Voice has its own module with
the case-vs-voice gate; this covers the rest.) Marker-based, no role gating.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))


def feature_hypotheses(pair: str, features: tuple[str, ...], *, sample: int = 200,
                       min_lift: float = 2.0, min_share: float = 0.25) -> dict:
    from review.affix_function import induce_affix_functions
    af = induce_affix_functions(pair, sample=sample)
    funcs = af.get("functions", {})
    cells = []
    for aff, d in funcs.items():
        fn = str(d.get("function", ""))
        feat = fn.split("=")[0]
        if feat in features and (d.get("lift") or 0) >= min_lift and (d.get("share") or 0) >= min_share:
            form = aff.split("(")[0]
            cells.append({"markers": [form], "function": fn, "feature": fn,
                          "lift": d.get("lift"), "share": d.get("share"),
                          "heldout": d.get("heldout_accuracy")})
    cells.sort(key=lambda c: -(c.get("lift") or 0))
    return {"pair": pair, "cells": cells, "n": len(cells), "features": list(features)}


def detect_feature_paradigm(pair: str, features: tuple[str, ...], *, sample: int = 200,
                            min_cells: int = 1) -> tuple[bool, float, str, dict]:
    try:
        h = feature_hypotheses(pair, features, sample=sample)
    except Exception as e:  # noqa: BLE001
        return False, 0.3, f"feature-affix detector could not run ({type(e).__name__}: {e})", {}
    cells = h["cells"]
    if len(cells) >= min_cells:
        ex = ", ".join(f"{c['markers'][0]}→{c['function']}" for c in cells[:4])
        return True, round(min(0.8, 0.5 + 0.1 * len(cells)), 2), f"{len(cells)} feature-marked affixes: {ex}", h
    return False, 0.45, f"{len(cells)} feature-marked affixes — no paradigm", h
