"""TAM detector — verb tense/aspect affixes, recovered by projecting the English-pivot Tense onto the
verb's affixes (reuses `review.project.label_tam`, which derives e.g. swh na→Pres, li→Past from data).
Marker-based (the affix is the marker); no role gating."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))


# English TAM words → grammatical label, for ANALYTIC tense particles (isolating/analytic langs mark
# tense with free words: vie đã/sẽ/đang, ind sudah/akan/sedang) — recovered by the particle's alignment.
_TAM_EN = {"will": "future", "shall": "future", "have": "perfect", "has": "perfect", "had": "perfect",
           "was": "progressive", "were": "progressive", "being": "progressive"}


def _analytic_tam(pair: str, *, top_words: int = 150, max_len: int = 6, min_prob: float = 0.14) -> list[dict]:
    """High-frequency closed-class words that align to an English TAM word = analytic tense particles."""
    from induce.tdd import load_freqs
    from review.paradigm.postp_detect import _glosses
    freqs = load_freqs(pair)
    gl = _glosses(pair)
    out = []
    for w, _c in freqs.most_common(top_words):
        if len(w) > max_len:
            continue
        en, prob = gl.get(w, ("", 0.0))
        if en in _TAM_EN and prob >= min_prob:
            out.append({"markers": [w], "tense": _TAM_EN[en], "function": f"Tense={_TAM_EN[en]}",
                        "en": en, "prob": round(prob, 3), "src": "particle"})
    return out


def tam_hypotheses(pair: str, *, sample: int = 300) -> dict:
    """Verb TAM cells from THREE paths: PREFIX tense via project.label_tam (swh na-/li-/ta-), SUFFIXAL
    tense/aspect via the feature-predictor (spa -ndo/-ó, rus -л, tur -dI), and ANALYTIC particles via
    alignment (vie đã/sẽ/đang, ind sudah/akan). Merged + deduped."""
    cells = []
    seen = set()
    from review.project import label_tam
    for m, d in sorted(label_tam(pair, sample=sample).get("derived_tam_labels", {}).items(),
                       key=lambda kv: -kv[1].get("n", 0)):
        cells.append({"markers": [m], "tense": d.get("tense"), "function": f"Tense={d.get('tense')}",
                      "n": d.get("n"), "confidence": d.get("confidence"), "src": "prefix"})
        seen.add(m)
    from review.paradigm.feature_affix_detect import feature_hypotheses
    fh = feature_hypotheses(pair, ("Tense", "Aspect", "Mood", "VerbForm"), sample=sample,
                            min_lift=2.0, min_share=0.2)
    for c in fh["cells"]:
        if c["markers"][0] not in seen:
            cells.append({"markers": c["markers"], "tense": c["function"].split("=")[-1],
                          "function": c["function"], "lift": c.get("lift"), "src": "suffix"})
            seen.add(c["markers"][0])
    for c in _analytic_tam(pair):
        if c["markers"][0] not in seen:
            cells.append(c)
            seen.add(c["markers"][0])
    return {"pair": pair, "tam": cells, "n_tam": len(cells)}


def detect_tam(pair: str, *, sample: int = 200) -> tuple[bool, float, str, dict]:
    """Present when >= 2 verb affixes carry a tense/aspect/verb-form label (prefix or suffix)."""
    try:
        h = tam_hypotheses(pair, sample=sample)
    except Exception as e:  # noqa: BLE001
        return False, 0.3, f"tam detector could not run ({type(e).__name__}: {e})", {}
    cells = [c for c in h["tam"]
             if ((c.get("confidence") or 0) >= 0.5 and (c.get("n") or 0) >= 8)
             or (c.get("lift") or 0) >= 2.0 or (c.get("prob") or 0) >= 0.14]
    if len(cells) >= 2:
        ex = ", ".join(f"{c['markers'][0]}→{c['function']}" for c in cells[:4])
        return True, round(min(0.85, 0.5 + 0.06 * len(cells)), 2), f"{len(cells)} TAM-marked affixes: {ex}", h
    return False, 0.45, f"{len(cells)} TAM-marked affixes — no TAM paradigm", h
