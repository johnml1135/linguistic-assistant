"""Offline tests for affix-function induction: the pure cooccur/rank core finds the feature value an affix
predicts above its base rate, and gates on support/share/lift. No parser/corpus needed."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import affix_function as AF   # noqa: E402


def test_cooccur_and_rank_finds_plural_suffix():
    # suffix -s marks Number=Plur: every -s word is Plural; non -s words are mostly Singular
    rows = [(f"cat{i}s", {"Number": "Plur"}) for i in range(10)]
    rows += [(f"dog{i}", {"Number": "Sing"}) for i in range(10)]
    affixes = [("s", "suffix")]
    ranked = AF.rank_functions(*AF.cooccur(rows, affixes))
    assert ranked[("s", "suffix")]["function"] == "Number=Plur"
    assert ranked[("s", "suffix")]["share"] == 1.0 and ranked[("s", "suffix")]["lift"] > 1.5


def test_rank_rejects_below_lift_or_support():
    # 'a' co-occurs with Number=Sing at exactly the base rate (no lift) -> not labelled
    rows = [(f"a{i}", {"Number": "Sing"}) for i in range(6)] + [(f"b{i}", {"Number": "Sing"}) for i in range(6)]
    ranked = AF.rank_functions(*AF.cooccur(rows, [("a", "prefix")]))
    assert ("a", "prefix") not in ranked            # feature is universal -> lift ~1.0, rejected

    # below MIN_SUPPORT -> not labelled even with perfect share
    rows2 = [("xz", {"Tense": "Past"}), ("xy", {"Tense": "Past"})]
    ranked2 = AF.rank_functions(*AF.cooccur(rows2, [("x", "prefix")]))
    assert ("x", "prefix") not in ranked2


def test_bears_boundary():
    assert AF._bears("watu", "wa", "prefix") and not AF._bears("wa", "wa", "prefix")   # needs >1 residue
    assert AF._bears("books", "s", "suffix") and not AF._bears("as", "s", "suffix")


if __name__ == "__main__":
    import traceback

    class _MP:
        pass

    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for name, fn in fns:
        try:
            fn(); passed += 1; print(f"  ok  {name}")
        except Exception:
            print(f"FAIL  {name}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    raise SystemExit(0 if passed == len(fns) else 1)
