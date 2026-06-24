"""Offline tests for the glide-collapse promotion path: glide-shape detection + the round-trip-gated
classification (the HC round-trip itself is mocked so these run without hc.exe)."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import promote as P   # noqa: E402


def _cand(members, vocalic=True, examples=None):
    rule = {"members": members, "alternating": {"vocalic": vocalic},
            "evidence": {"support": {m: 100 for m in members}, "examples": examples or {}}}
    return P.RuleCandidate(id="_".join(members) + "_collapse", pair="swh", kind="glide-collapse",
                           description="test", members=members, support=200, rule=rule)


def test_glide_shape_detects_mu_mw():
    s = P._glide_shape({"members": ["mu", "mw"], "alternating": {"vocalic": True}})
    assert s and s["ur"] == "mu" and s["vowel"] == "u" and s["glide"] == "w" and s["glide_form"] == "mw"


def test_glide_shape_detects_vi_vy():
    s = P._glide_shape({"members": ["vi", "vy"], "alternating": {"vocalic": True}})
    assert s and s["ur"] == "vi" and s["glide_form"] == "vy"


def test_glide_shape_rejects_non_glide():
    # p/pe alternates a non-high vowel 'e' (no glide) → not a glide collapse
    assert P._glide_shape({"members": ["p", "pe"], "alternating": {"vocalic": True}}) is None
    # non-vocalic alternation → not a glide collapse
    assert P._glide_shape({"members": ["men", "mem"], "alternating": {"vocalic": False}}) is None


def test_verify_promotes_when_within_tolerance(monkeypatch):
    # no exceptions in the rule's environment → productive → promote
    monkeypatch.setattr(P, "_verify_collapse",
                        lambda c: {"ran": True, "n_env": 40, "n_exceptions": 0, "recall_env": 1.0, "failures": []})
    cand = P.classify(P.verify(_cand(["mu", "mw"])))
    assert cand.buildable is True and cand.recall == 1.0
    assert cand.classification == "promote"


def test_verify_defers_when_exceptions_exceed_tolerance(monkeypatch):
    # 12 exceptions over 30 in-env items: 30/ln30 ≈ 8.8 < 12 → not productive → defer (never force-promoted)
    monkeypatch.setattr(P, "_verify_collapse",
                        lambda c: {"ran": True, "n_env": 30, "n_exceptions": 12, "recall_env": 0.6, "failures": ["x"]})
    cand = P.classify(P.verify(_cand(["vi", "vy"])))
    assert cand.buildable is False
    assert cand.classification == "defer"


def test_verify_tolerates_bounded_exceptions(monkeypatch):
    # 3 exceptions over 40: 40/ln40 ≈ 10.8 > 3 → productive despite a few lexical exceptions → promote
    monkeypatch.setattr(P, "_verify_collapse",
                        lambda c: {"ran": True, "n_env": 40, "n_exceptions": 3, "recall_env": 0.925, "failures": ["x"]})
    cand = P.classify(P.verify(_cand(["mu", "mw"])))
    assert cand.buildable is True and cand.classification == "promote"


def test_non_glide_collapse_is_not_buildable():
    cand = P.RuleCandidate(id="p_pe_collapse", pair="swh", kind="allomorph-collapse",
                           description="p~pe", members=["p", "pe"], support=200,
                           rule={"members": ["p", "pe"], "alternating": {"vocalic": True}, "evidence": {}})
    cand = P.classify(P.verify(cand))
    assert cand.buildable is False and cand.classification == "defer"


if __name__ == "__main__":
    import traceback

    class _MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for name, fn in fns:
        try:
            fn(_MP()) if "monkeypatch" in fn.__code__.co_varnames else fn()
            passed += 1; print(f"  ok  {name}")
        except Exception:
            print(f"FAIL  {name}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    raise SystemExit(0 if passed == len(fns) else 1)
