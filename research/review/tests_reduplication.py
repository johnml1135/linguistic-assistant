"""Offline tests for the reduplication detector (pure; corpus scan gated)."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import reduplication as R   # noqa: E402


def test_detects_initial_cv_reduplication():
    # textbook Tagalog aspect reduplication
    assert R.is_reduplicated("susulat") == 2        # su·sulat
    assert R.is_reduplicated("tatakbo") == 2        # ta·takbo
    assert R.is_reduplicated("gagawin") == 2        # ga·gawin
    assert R.is_reduplicated("aalis") == 1          # a·alis (vowel copy)


def test_rejects_non_reduplicated():
    assert R.is_reduplicated("sulat") is None
    assert R.is_reduplicated("kitabu") is None
    assert R.is_reduplicated("abc") is None         # too short
    assert R.is_reduplicated("tt") is None          # copy has no vowel / too short


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
