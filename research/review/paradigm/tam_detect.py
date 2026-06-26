"""TAM detector — verb tense/aspect affixes, recovered by projecting the English-pivot Tense onto the
verb's affixes (reuses `review.project.label_tam`, which derives e.g. swh na→Pres, li→Past from data).
Marker-based (the affix is the marker); no role gating."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))


def tam_hypotheses(pair: str, *, sample: int = 300) -> dict:
    from review.project import label_tam
    r = label_tam(pair, sample=sample)
    labels = r.get("derived_tam_labels", {})
    cells = [{"markers": [m], "tense": d.get("tense"), "n": d.get("n"), "confidence": d.get("confidence")}
             for m, d in sorted(labels.items(), key=lambda kv: -kv[1].get("n", 0))]
    return {"pair": pair, "tam": cells, "n_tam": len(cells)}


def detect_tam(pair: str, *, sample: int = 200) -> tuple[bool, float, str, dict]:
    """Present when >= 2 verb affixes carry a derived tense label (a TAM paradigm)."""
    try:
        h = tam_hypotheses(pair, sample=sample)
    except Exception as e:  # noqa: BLE001
        return False, 0.3, f"tam detector could not run ({type(e).__name__}: {e})", {}
    cells = [c for c in h["tam"] if (c.get("confidence") or 0) >= 0.5 and (c.get("n") or 0) >= 8]
    if len(cells) >= 2:
        ex = ", ".join(f"{c['markers'][0]}→{c['tense']}" for c in cells[:4])
        return True, round(min(0.85, 0.5 + 0.08 * len(cells)), 2), f"{len(cells)} tense-marked affixes: {ex}", h
    return False, 0.45, f"{len(cells)} tense-marked affixes — no TAM paradigm", h
