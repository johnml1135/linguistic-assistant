"""Offline tests for the class-system lifecycle: the confidence tier, the pure suggest/assign/flag logic,
the declare commit-gate, and the profile round-trip of the declared schema (compile root)."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import classes as C   # noqa: E402


# ── confidence tier ─────────────────────────────────────────────────────────────────────────────────────
def test_route_foundational_never_auto():
    r = C.route("class_system", 0.999)
    assert r["lane"] == "review"                       # the compile root never auto-commits, even at 0.999


def test_route_leaf_auto_when_verified_confident():
    r = C.route("class_assignment", 0.95, bar=0.9)
    assert r["lane"] == "auto" and r["reversible"] is True and "good enough" in r["stamp"]


def test_route_leaf_review_when_unsure():
    assert C.route("class_assignment", 0.5, bar=0.9)["lane"] == "review"


# ── suggest (pure) ──────────────────────────────────────────────────────────────────────────────────────
def test_ending_gender():
    assert C._ending_gender("libro") == "m"
    assert C._ending_gender("casa") == "f" and C._ending_gender("nación") == "f"
    assert C._ending_gender("luz") is None


def _votes():
    return {"libro": Counter({"M": 9, "F": 0}), "mesa": Counter({"M": 0, "F": 8}),
            "agua": Counter({"M": 11, "F": 0}),            # masc article, but ends -a → the exception
            "casa": Counter({"M": 1, "F": 12})}


def test_build_gender_classes():
    s = C.build_gender_classes(_votes())
    ids = {c["id"] for c in s["classes"]}
    assert ids == {"m", "f"} and s["status"] == "proposed" and s["strategy"] == "gender-by-article"
    m = next(c for c in s["classes"] if c["id"] == "m")
    assert m["concord"]["def_art_sg"] == "el" and m["concord"]["adjective_suffix"] == "o"
    assert s["alternatives"]                            # the subjective cut is surfaced, not decided


# ── utilize (pure) ──────────────────────────────────────────────────────────────────────────────────────
def test_assign_from_votes_respects_declared_ids():
    schema = {"classes": [{"id": "m"}, {"id": "f"}]}
    a = C.assign_from_votes(_votes(), schema)
    assert a["libro"]["class"] == "m" and a["casa"]["class"] == "f"
    assert a["libro"]["confidence"] > 0.9              # 9/9 agreement, full support → high, auto-pushable


def test_build_bantu_classes():
    clusters = {"m": ["mtu", "mti"], "wa": ["watu", "watoto"], "ki": ["kitu", "kiti"], "vi": ["vitu", "viti"]}
    s = C.build_bantu_classes(clusters)
    ids = {c["id"] for c in s["classes"]}
    assert "2" in ids and "7" in ids and "8" in ids       # wa-, ki-, vi- classes present
    cl13 = next(c for c in s["classes"] if c["id"] == "1/3")
    assert "mtu" in cl13["evidence"]["examples"] and cl13["concord"] == {}   # concord deferred
    assert any("persons) vs cl3" in alt["option"] for alt in s["alternatives"])  # the subjective split surfaced


def test_flag_exceptions_catches_el_agua():
    a = C.assign_from_votes(_votes(), {"classes": [{"id": "m"}, {"id": "f"}]})
    flags = C.flag_exceptions(_votes(), a)
    nouns = {f["noun"] for f in flags}
    assert "agua" in nouns                              # masc article + -a ending → flagged
    assert "libro" not in nouns and "casa" not in nouns  # consistent nouns are not flagged


# ── declare commit-gate (monkeypatched profile — no disk) ───────────────────────────────────────────────
class _FakeProfile:
    def __init__(self):
        self.class_schema = {}

    def auto_accept_bar(self):
        return 0.995


def test_declare_commits_and_versions(monkeypatch):
    fake = _FakeProfile()
    from review.deferrals import profile as P
    monkeypatch.setattr(P, "load", lambda pair: fake)
    monkeypatch.setattr(P, "save", lambda prof: None)
    committed = C.declare("spa", C.build_gender_classes(_votes()), by="ai-accepted")
    assert committed["status"] == "declared" and committed["version"] == 1
    assert committed["declared_by"] == "ai-accepted" and fake.class_schema["status"] == "declared"
    # a second declare bumps the version
    committed2 = C.declare("spa", C.build_gender_classes(_votes()))
    assert committed2["version"] == 2 and committed2["declared_by"] == "human"


def test_profile_roundtrips_class_schema():
    from review.deferrals.profile import LanguageProfile
    p = LanguageProfile(pair="spa", class_schema={"status": "declared", "version": 3, "classes": []})
    p2 = LanguageProfile.from_dict(p.to_dict())
    assert p2.class_schema == {"status": "declared", "version": 3, "classes": []}


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
