"""Offline tests for concord induction (the pure builder; corpus scan is gated)."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import agreement as AG   # noqa: E402


def test_prefix_longest_match():
    assert AG._prefix("watu") == "wa" and AG._prefix("kitu") == "ki" and AG._prefix("vyombo") == "vy"
    assert AG._prefix("ndege") == "n" and AG._prefix(" a") == "Ø"


def test_build_concord_fills_clear_alliterative_cells():
    schema = {"classes": [{"id": "2", "prefixes": ["wa"]}, {"id": "7", "prefixes": ["ki"]}]}
    votes = {"wa": Counter({"wa": 300, "Ø": 50}), "ki": Counter({"ki": 100, "Ø": 10})}
    filled = AG.build_concord(votes, schema, min_support=20, min_share=0.5)
    assert filled["2"]["adjective"] == "wa" and filled["7"]["adjective"] == "ki"


def test_build_concord_skips_weak_or_all_O():
    schema = {"classes": [{"id": "6", "prefixes": ["ma"]}, {"id": "9/10", "prefixes": ["n"]}]}
    votes = {"ma": Counter({"Ø": 900, "ma": 3}),     # adjective surfaces bare → no class signal
             "n": Counter({"Ø": 800})}               # all Ø → nothing to fill
    filled = AG.build_concord(votes, schema, min_support=20, min_share=0.5)
    assert "6" not in filled and "9/10" not in filled   # honest: leave the cell empty


def test_classify_zero_prefix_by_associative():
    # zero-prefix nouns classified by the associative they trigger (Corbett): ya→9/10, la→5
    zero = {"siku": Counter({"ya": 40}), "jina": Counter({"la": 12}), "x": Counter({"wa": 9})}
    out = AG.classify_zero_prefix(zero)
    assert out["siku"]["class"] == "9/10" and out["jina"]["class"] == "5"
    assert "x" not in out                              # 'wa' is ambiguous across classes → not classified


def test_build_associative_concord():
    schema = {"classes": [{"id": "7", "prefixes": ["ki"]}, {"id": "9/10", "prefixes": ["n"]}]}
    by_pfx = {"ki": Counter({"cha": 200, "kwa": 20}), "n": Counter({"ya": 300, "la": 10})}
    filled = AG.build_associative_concord(by_pfx, schema, min_support=20, min_share=0.4)
    assert filled["7"]["associative"] == "cha" and filled["9/10"]["associative"] == "ya"


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
