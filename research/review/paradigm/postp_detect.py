"""Postpositional (analytic) case detector — for SOV+postpositional languages (hin) where role projection
fails (English SVO+prepositional misaligns), but each case-marking POSTPOSITION is a high-frequency
closed-class word that aligns 1:1 to an English adposition. So we recover the case inventory from the
postpositions' own THOT alignment, not from role covariation:

  hin का/की/के → "of" (genitive), को → "to" (dative), में → "in" (locative), से → "from" (ablative),
      पर → "on" (locative). ने (ergative) has no English equivalent → the honest miss.

The case FUNCTION comes from the (universal) English adposition the marker aligns to — a pivot signal,
not recalled language knowledge.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

# English adposition → case function (universal pivot mapping, not language-specific)
_ADPOS = {"of": "genitive", "to": "dative", "for": "benefactive", "in": "locative", "into": "locative",
          "at": "locative", "on": "locative", "from": "ablative", "by": "instrumental",
          "with": "instrumental", "until": "terminative", "till": "terminative", "through": "perlative"}


def _glosses(pair: str) -> dict:
    """target word -> (best English, prob) from the regenerated glosses.tsv."""
    from gold.compile import PAIR_DIR
    g = _RESEARCH / "_sources" / "ebible" / PAIR_DIR[pair] / "glosses.tsv"
    out = {}
    if g.exists():
        for line in g.read_text(encoding="utf-8").splitlines()[1:]:
            p = line.split("\t")
            if len(p) >= 3:
                try:
                    out[p[0]] = (p[1], float(p[2]))
                except ValueError:
                    pass
    return out


def postposition_hypotheses(pair: str, *, top_words: int = 40, max_len: int = 4, min_prob: float = 0.35) -> dict:
    """High-frequency short closed-class words that align to an English adposition = the case postpositions."""
    from induce.tdd import load_freqs
    freqs = load_freqs(pair)
    gl = _glosses(pair)
    cells = []
    for w, _c in freqs.most_common(top_words):
        if len(w) > max_len:
            continue
        en, prob = gl.get(w, ("", 0.0))
        if en in _ADPOS and prob >= min_prob:
            cells.append({"markers": [w], "en": en, "function": _ADPOS[en], "prob": round(prob, 3),
                          "count": freqs.get(w, 0)})
    # dedupe by function, keep the strongest marker per function but list all markers of that function
    by_fn: dict[str, dict] = {}
    for c in sorted(cells, key=lambda c: -c["prob"]):
        fn = c["function"]
        if fn not in by_fn:
            by_fn[fn] = {"markers": [], "function": fn, "en": c["en"], "prob": c["prob"]}
        by_fn[fn]["markers"].extend(c["markers"])
    return {"pair": pair, "rows": list(by_fn.values()), "n_markers": len(cells),
            "n_cases": len(by_fn)}


def detect_postp_case(pair: str, **_) -> tuple[bool, float, str, dict]:
    """Present when >= 2 distinct case functions are marked by adposition-aligned postpositions."""
    try:
        h = postposition_hypotheses(pair)
    except Exception as e:  # noqa: BLE001
        return False, 0.3, f"postposition detector could not run ({type(e).__name__}: {e})", {}
    rows = h["rows"]
    if len(rows) >= 2:
        ex = ", ".join(f"{r['markers'][0]}→{r['function']}" for r in rows[:5])
        return True, round(min(0.85, 0.5 + 0.08 * len(rows)), 2), \
            f"{len(rows)} postposition-marked cases ({ex})", h
    return False, 0.45, f"{len(rows)} postposition cases — no analytic case system", h
