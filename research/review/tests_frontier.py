"""Offline tests for the frontier finder: ranking (ready chunks by unexplained mass, not-ready excluded)
and catalog integrity. Probes are monkeypatched so this runs without corpus/gold."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import frontier as F   # noqa: E402


def test_catalog_covers_the_dozen_types():
    ids = {cid for cid, _, _ in F.CATALOG}
    assert {"switches", "classes", "agreement", "additive_affixes", "allomorphy"} <= ids
    assert len(F.CATALOG) >= 10


def test_frontier_ranks_ready_by_unexplained(monkeypatch):
    monkeypatch.setattr(F, "_build_ctx", lambda pair, sample=0: {"pair": pair})
    monkeypatch.setattr(F, "PROBES", {
        "classes": lambda ctx: {"unexplained": 0.30, "ready": True, "evidence": "c", "action": "a"},
        "agreement": lambda ctx: {"unexplained": 0.60, "ready": True, "evidence": "g", "action": "a"},
        "switches": lambda ctx: {"unexplained": 0.95, "ready": False, "evidence": "s", "action": "a"},
    })
    f = F.frontier("xx")
    assert f["next"]["id"] == "agreement"                 # highest unexplained AMONG ready
    assert [r["id"] for r in f["ranked"]] == ["agreement", "classes"]   # switches excluded (not ready)


def test_frontier_marks_unprobed_as_pending(monkeypatch):
    monkeypatch.setattr(F, "_build_ctx", lambda pair, sample=0: {"pair": pair})
    monkeypatch.setattr(F, "PROBES", {"classes": lambda ctx: {"unexplained": 0.2, "ready": True,
                                                              "evidence": "c", "action": "a"}})
    f = F.frontier("xx")
    pend = {r["id"] for r in f["rows"] if r.get("probe") == "pending"}
    assert "morphotactics" in pend and "orthography" in pend   # no probe yet → pending, not scored 0


def test_proxy_never_drives_the_recommendation(monkeypatch):
    monkeypatch.setattr(F, "_build_ctx", lambda pair, sample=0: {"pair": pair})
    monkeypatch.setattr(F, "PROBES", {
        "allomorphy": lambda ctx: {"unexplained": 1.0, "ready": True, "proxy": True, "evidence": "p", "action": "a"},
        "classes": lambda ctx: {"unexplained": 0.1, "ready": True, "evidence": "c", "action": "a"},
    })
    f = F.frontier("xx")
    assert f["next"]["id"] == "classes"                   # the true-coverage signal, not the hot proxy
    assert f["ranked"][0]["id"] == "allomorphy"           # proxy still visible in the ranked list


def test_frontier_handles_all_not_ready(monkeypatch):
    monkeypatch.setattr(F, "_build_ctx", lambda pair, sample=0: {"pair": pair})
    monkeypatch.setattr(F, "PROBES", {"agreement": lambda ctx: {"unexplained": 0.9, "ready": False,
                                                               "evidence": "x", "action": "—"}})
    assert F.frontier("xx")["next"] is None               # nothing ready → no next chunk (honest)


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
