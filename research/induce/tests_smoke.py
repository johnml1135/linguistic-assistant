"""Offline smoke tests for the phonology-induction loop (Phase 1, text-only).

Run: `python research/cycle/tests_smoke.py` (also pytest-discoverable).
No `hc.exe`, no network, no audio — the harmony-rule expander is the offline oracle
(it IS the generate direction of the induced rule, exactly what HC would compute).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from induce.phonology import (  # noqa: E402
    HARMONY_CLASSES,
    collapse_families,
    enumeration_debt,
    expand_archiphoneme,
    propose_archiphoneme,
)


def test_front_height_family_collapses_to_one_archiphoneme():
    # Swahili causative -ish-/-esh- (height harmony): one archiphoneme over the front {i,e} class.
    prop = propose_archiphoneme(["isha", "esha"], HARMONY_CLASSES["swh"])
    assert prop is not None
    assert prop.archiphoneme == "Esha"
    assert prop.collapsible is True
    assert prop.generated == {"isha", "esha"}


def test_back_height_family_collapses():
    # Swahili reversive -u-/-o- (back height pair).
    prop = propose_archiphoneme(["ua", "oa"], HARMONY_CLASSES["swh"])
    assert prop is not None
    assert prop.archiphoneme == "Oa"
    assert prop.collapsible is True
    assert prop.generated == {"ua", "oa"}


def test_expand_archiphoneme_regenerates_observed_surfaces():
    assert expand_archiphoneme("Esha", HARMONY_CLASSES["swh"]) == {"isha", "esha"}
    assert expand_archiphoneme("Eka", HARMONY_CLASSES["swh"]) == {"ika", "eka"}  # stative -ik-/-ek-


def test_cross_class_family_is_not_auto_collapsible():
    # 'i' is in the front height class, 'o' in the back one -> no single clean class -> needs review.
    prop = propose_archiphoneme(["isha", "osha"], HARMONY_CLASSES["swh"])
    assert prop is None or prop.collapsible is False


def test_multi_position_family_is_not_auto_collapsible():
    # Two differing vowel positions -> conservative: needs review, never an auto-collapse.
    prop = propose_archiphoneme(["isha", "eshe"], HARMONY_CLASSES["swh"])
    assert prop is None or prop.collapsible is False


def test_consonant_difference_is_not_a_harmony_alternation():
    prop = propose_archiphoneme(["ika", "ipa"], HARMONY_CLASSES["swh"])
    assert prop is None or prop.collapsible is False


def test_collapse_families_reduces_enumeration_debt_to_residual():
    families = {
        "sh": ["isha", "esha"],   # causative -> collapses
        "k": ["ika", "eka"],      # stative  -> collapses
        "x": ["isha", "osha"],    # over-merged junk family (cross-class) -> stays as debt
    }
    assert enumeration_debt(families) == (2 - 1) + (2 - 1) + (2 - 1)  # = 3
    report = collapse_families(families, HARMONY_CLASSES["swh"])
    assert report.debt_before == 3
    assert sorted(p.archiphoneme for p in report.collapsed) == ["Eka", "Esha"]
    assert report.debt_after == 1  # only the junk 'x' family remains
    assert report.affixes_removed == (2 - 1) + (2 - 1)  # 2 redundant allomorphs collapsed away


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
