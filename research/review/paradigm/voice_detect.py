"""Voice/focus detector (the 4th detector family — Austronesian) built on `review/affix_function.py`.

Voice is realised by verb affixes. The held-out feature-predictor labels the markable PASSIVE cleanly
(ind di- → Voice=Pass), but the ACTIVE is unmarked in the English pivot (meN- looks like nothing in
English), so we recover it structurally: the most productive verb prefix/infix that is NOT the passive is
the candidate active alternant. The packet carries both — the labelled passive + the candidate alternants.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))


def voice_hypotheses(pair: str, *, sample: int = 200) -> dict:
    """Affixes the feature-predictor labels Voice=* (ranked by lift), plus the top productive prefixes/
    infixes as candidate voice alternants (the unmarked active)."""
    from review.affix_function import induce_affix_functions
    from induce.morph_align import load_model
    af = induce_affix_functions(pair, sample=sample)
    funcs = af.get("functions", {})
    labelled = []
    for aff, d in funcs.items():
        fn = str(d.get("function", ""))
        if fn.startswith("Voice="):
            form = aff.split("(")[0]
            kind = aff.split("(")[1].rstrip(")") if "(" in aff else "prefix"
            labelled.append({"markers": [form], "kind": kind, "voice": fn.split("=", 1)[1],
                             "lift": d.get("lift"), "share": d.get("share"),
                             "heldout": d.get("heldout_accuracy")})
    labelled.sort(key=lambda c: -(c.get("lift") or 0))
    # candidate alternants: top productive prefixes/infixes (the active is unmarked → no Voice label)
    m = load_model(pair)
    aff_forms = [(a.form, a.kind, a.count) for a in m.affixes if a.kind in ("prefix", "infix")]
    aff_forms.sort(key=lambda t: -t[2])
    labelled_forms = {c["markers"][0] for c in labelled}
    candidates = [{"markers": [f], "kind": k, "count": c}
                  for f, k, c in aff_forms if f not in labelled_forms][:6]
    return {"pair": pair, "voice_affixes": labelled, "candidate_alternants": candidates,
            "n_voice": len(labelled), "n_affixes": af.get("n_affixes")}


def detect_voice(pair: str, *, sample: int = 200) -> tuple[bool, float, str, dict]:
    """Present when >= 1 affix predicts Voice above chance (a real passive marker). Gated to languages with
    no case (voice-focus is the Austronesian alternative to case marking) to avoid case-lang false-positives."""
    try:
        from review.deferrals.profile_detect import _cycle_affixes, _freqs, detect_synthesis  # noqa: F401
        # voice-focus langs are affixing with NO case; if a case system is present this isn't a voice lang
        from review.paradigm.case_detect import detect_case_real
        if detect_case_real(pair)[0] == "present":
            return False, 0.6, "case present → voice-focus is the Austronesian no-case alternative; not here", {}
    except Exception:
        pass
    try:
        h = voice_hypotheses(pair, sample=sample)
    except Exception as e:  # noqa: BLE001
        return False, 0.3, f"voice detector could not run ({type(e).__name__}: {e})", {}
    strong = [c for c in h["voice_affixes"] if (c.get("lift") or 0) >= 2.0 and (c.get("share") or 0) >= 0.25]
    if strong:
        ex = ", ".join(f"{c['markers'][0]}→Voice={c['voice']}(lift {c['lift']:.1f})" for c in strong[:3])
        return True, round(min(0.8, 0.5 + 0.1 * len(strong)), 2), f"voice marker(s): {ex}", h
    return False, 0.45, "no affix predicts Voice above chance", h
