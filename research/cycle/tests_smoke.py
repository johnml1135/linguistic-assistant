"""Offline smoke tests for the phonology-induction loop (Phase 1, text-only).

Run: `python research/cycle/tests_smoke.py` (also pytest-discoverable).
No `hc.exe`, no network, no audio — the harmony-rule expander is the offline oracle
(it IS the generate direction of the induced rule, exactly what HC would compute).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cycle.phonology import (  # noqa: E402
    HARMONY_CLASSES,
    collapse_families,
    enumeration_debt,
    expand_archiphoneme,
    propose_archiphoneme,
)


def test_two_way_low_vowel_family_collapses_to_one_archiphoneme():
    prop = propose_archiphoneme(["lar", "ler"], HARMONY_CLASSES["tur"])
    assert prop is not None
    assert prop.archiphoneme == "lAr"
    assert prop.collapsible is True
    assert prop.generated == {"lar", "ler"}


def test_four_way_high_vowel_family_collapses():
    prop = propose_archiphoneme(["nın", "nin", "nun", "nün"], HARMONY_CLASSES["tur"])
    assert prop is not None
    assert prop.archiphoneme == "nIn"
    assert prop.collapsible is True
    assert {"nın", "nin", "nun", "nün"} <= prop.generated


def test_expand_archiphoneme_regenerates_observed_surfaces():
    assert expand_archiphoneme("lAr", HARMONY_CLASSES["tur"]) == {"lar", "ler"}
    assert expand_archiphoneme("dAn", HARMONY_CLASSES["tur"]) == {"dan", "den"}


def test_cross_class_family_is_not_auto_collapsible():
    # 'a' is a low-unrounded harmony vowel; 'ö' is not in the same class -> no clean rule.
    prop = propose_archiphoneme(["an", "ön"], HARMONY_CLASSES["tur"])
    assert prop is None or prop.collapsible is False


def test_multi_position_family_is_not_auto_collapsible():
    # Two differing vowel positions -> conservative: needs review, never an auto-collapse.
    prop = propose_archiphoneme(["lara", "lere"], HARMONY_CLASSES["tur"])
    assert prop is None or prop.collapsible is False


def test_consonant_difference_is_not_a_harmony_alternation():
    prop = propose_archiphoneme(["lar", "nar"], HARMONY_CLASSES["tur"])
    assert prop is None or prop.collapsible is False


def test_hungarian_nak_nek_collapses():
    prop = propose_archiphoneme(["nak", "nek"], HARMONY_CLASSES["hun"])
    assert prop is not None
    assert prop.archiphoneme == "nAk"
    assert prop.collapsible is True


def test_collapse_families_reduces_enumeration_debt_to_residual():
    families = {
        "lr": ["lar", "ler"],
        "nn": ["nın", "nin", "nun", "nün"],
        "n": ["an", "ön"],  # over-merged junk family -> stays as debt
    }
    assert enumeration_debt(families) == (2 - 1) + (4 - 1) + (2 - 1)  # = 5
    report = collapse_families(families, HARMONY_CLASSES["tur"])
    assert report.debt_before == 5
    assert sorted(p.archiphoneme for p in report.collapsed) == ["lAr", "nIn"]
    assert report.debt_after == 1  # only the junk 'n' family remains
    assert report.affixes_removed == (2 - 1) + (4 - 1)  # 4 redundant allomorphs collapsed away


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
