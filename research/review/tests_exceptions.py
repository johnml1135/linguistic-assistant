"""Offline tests for the layered-exception carve + infix detection."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import exceptions as EX           # noqa: E402
from review import reduplication as R         # noqa: E402


def test_carve_finds_phonological_and_derivational_classes():
    ex = ["agua", "alma", "águila", "profeta", "bautista", "evangelista", "día", "mano"]
    c = EX.carve(ex, min_class=3)
    envs = {k["environment"] for k in c["classes"]}
    assert any("a-initial" in e for e in envs)      # el agua / el alma / el águila (phonological)
    assert any("-ta" in e for e in envs)            # bautista / evangelista / profeta (derivational)
    assert "día" in c["individuals"] and "mano" in c["individuals"]   # genuine individuals


def test_carve_no_spurious_initial_letter_classes():
    # raw single-initial grouping must NOT form classes (was the bug)
    c = EX.carve(["pongo", "patriarca", "pez", "xyz"], min_class=3)
    assert all("begins with 'p'" not in k["environment"] for k in c["classes"])


def test_infix_detection():
    stems = {"sulat", "bili", "basa"}
    assert R.is_infixed("sumulat", stems) == "um"
    assert R.is_infixed("binili", stems) == "in"
    assert R.is_infixed("sulat", stems) is None and R.is_infixed("aalis", stems) is None


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); passed += 1; print(f"  ok  {fn.__name__}")
        except Exception:
            print(f"FAIL  {fn.__name__}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    raise SystemExit(0 if passed == len(fns) else 1)
