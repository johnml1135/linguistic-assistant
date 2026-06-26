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


def _prefix_root_sets(pair, model) -> dict:
    """{prefix: set(roots it attaches to)} over frequent words — for complementary-distribution analysis."""
    from collections import defaultdict
    from induce.morph_align import segment_word
    from induce.tdd import load_freqs
    roots = sorted({e.form for e in model.lexicon if len(e.form) >= 3}, key=len, reverse=True)
    suff = sorted({a.form for a in model.affixes if a.kind == "suffix"}, key=len, reverse=True)
    pref = sorted({a.form for a in model.affixes if a.kind == "prefix"}, key=len, reverse=True)
    pre_roots: dict[str, set] = defaultdict(set)
    for w, _c in load_freqs(pair).most_common(2500):
        segs = segment_word(w, roots, suff, pref, [])
        rt = "".join(m for m, r in segs if r == "root")
        for m, r in segs:
            if r == "prefix" and rt:
                pre_roots[m].add(rt)
    return pre_roots


def active_alternants(pair, model, passive_form: str, *, min_overlap: float = 0.15) -> list[dict]:
    """The ACTIVE prefix is the unmarked voice (invisible to the English pivot), but it is the paradigmatic
    ALTERNANT of the passive: it attaches to the SAME roots (baca → di-baca / mem-baca). Recover it from
    vernacular-internal complementary distribution — prefixes whose root-set overlaps the passive's."""
    pr = _prefix_root_sets(pair, model)
    di_roots = pr.get(passive_form, set())
    if len(di_roots) < 3:
        return []
    out = []
    for p, roots in pr.items():
        if p == passive_form or len(roots) < 3:
            continue
        ov = len(roots & di_roots) / len(di_roots)
        if ov >= min_overlap:
            out.append({"markers": [p], "overlap": round(ov, 3), "n_shared": len(roots & di_roots)})
    out.sort(key=lambda c: -c["overlap"])
    return out[:5]


def voice_hypotheses(pair: str, *, sample: int = 200) -> dict:
    """Affixes the feature-predictor labels Voice=* (the passive), plus the ACTIVE recovered from internal
    complementary distribution (the alternant sharing roots with the passive)."""
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
    m = load_model(pair)
    passive = labelled[0]["markers"][0] if labelled else None
    actives = active_alternants(pair, m, passive) if passive else []
    return {"pair": pair, "voice_affixes": labelled, "active_alternants": actives,
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
