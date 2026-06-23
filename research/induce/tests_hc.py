"""HC-gated round-trip tests for archiphoneme + harmony grammars (Phase 1 task 1.1).

These require the Hermit Crab CLI (`hc`) and are **skipped** when it is absent, so CI stays green.
Run: `python research/cycle/tests_hc.py` (also pytest-discoverable; pytest skips when hc is missing).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from induce.hc_phonology import (  # noqa: E402
    SPANISH_CONSONANTS,
    SPANISH_VOWELS,
    Affix,
    build_harmony_grammar,
    collapse_round_trips,
    fold_spanish_accents,
    hc_available,
    run_parse,
)

try:  # skip (not fail) under pytest when the hc CLI is unavailable; still runnable as a plain script.
    import pytest

    pytestmark = pytest.mark.skipif(not hc_available(), reason="hc CLI not installed")
except ImportError:  # pragma: no cover
    pytest = None

# Verified ASCII stand-ins: a/e low; i/y front/back high unrounded; u/w back/front high rounded.
ROOTS = [("at", "horse"), ("ev", "house"), ("ut", "iron"), ("gwz", "eye")]


def test_low_archiphoneme_lAr_collapses_two_allomorphs():
    # -lAr (plural) must parse BOTH the back (atlar) and front (evler) surface allomorphs.
    ok = collapse_round_trips(
        ROOTS,
        Affix(id="r_plur", form="lAr", gloss="PL"),
        {"atlar": "horse PL", "evler": "house PL"},
    )
    assert ok


def test_high_archiphoneme_In_collapses_four_allomorphs():
    # -In (genitive) must parse ALL FOUR 4-way surfaces (back/front x round/unround).
    ok = collapse_round_trips(
        ROOTS,
        Affix(id="r_gen", form="In", gloss="GEN"),
        {"atyn": "horse GEN", "evin": "house GEN", "utun": "iron GEN", "gwzwn": "eye GEN"},
    )
    assert ok


def test_single_suffix_morpheme_covers_all_surfaces():
    # The whole point: ONE morpheme, not N listed allomorphs — every surface maps to the same morph.
    xml = build_harmony_grammar(ROOTS, [Affix(id="r_gen", form="In", gloss="GEN")])
    parsed = run_parse(xml, ["atyn", "evin", "utun", "gwzwn"])
    suffix_morphs = set()
    for surface in ("atyn", "evin", "utun", "gwzwn"):
        analyses = parsed[surface]
        assert analyses, f"{surface} did not parse"
        suffix_morphs.add(analyses[0][-1][0])  # the suffix morph form of the first analysis
    assert len(suffix_morphs) == 1, f"expected one shared suffix morpheme, got {suffix_morphs}"


def test_spanish_feature_inventory_parses_a_concatenative_grammar():
    # The Spanish slice's #1-gap closer: a REAL grapheme→feature inventory (no harmony rules) parses
    # real Spanish forms in hc. Plural -s on vowel-final stems: casa→casas, amigo→amigos.
    xml = build_harmony_grammar(
        [("casa", "house"), ("amigo", "friend")],
        [Affix(id="r_pl", form="s", gloss="PL")],
        vowels=SPANISH_VOWELS,
        consonants=SPANISH_CONSONANTS,
        include_harmony_rules=False,
    )
    parsed = run_parse(xml, ["casas", "amigos"])
    for surface, expected in (("casas", "house PL"), ("amigos", "friend PL")):
        analyses = parsed.get(surface, [])
        assert analyses, f"{surface} did not parse against the Spanish inventory"
        assert expected in {" ".join(g for _, g in a) for a in analyses}, f"{surface}: missing {expected!r}"


def test_fold_spanish_accents_maps_to_base_vowels():
    assert fold_spanish_accents("Jesús") == "Jesus"
    assert fold_spanish_accents("oración") == "oracion"


def test_infix_rule_round_trips_through_golden_hc():
    # Tagalog-style infix: root `sulat` + `-um-` after the onset consonant → `sumulat` (s-um-ulat).
    from engine.grammar import Affix as GAffix
    from engine.grammar import LangModel, LexEntry
    from engine.hc import run_parse as golden_run_parse

    model = LangModel(
        code="tst",
        lexicon=[LexEntry(form="sulat", gloss="write"), LexEntry(form="basa", gloss="read")],
        affixes=[GAffix(form="um", gloss="<um>", kind="infix")],
    )
    parsed = golden_run_parse(model, ["sumulat", "bumasa"], templated=False)
    for surface, root_gloss in (("sumulat", "write"), ("bumasa", "read")):
        analyses = parsed.get(surface, [])
        assert analyses, f"{surface} did not parse against the infix rule"
        glosses = {" ".join(g for _, g in a) for a in analyses}
        assert any(root_gloss in gl and "<um>" in gl for gl in glosses), f"{surface}: {glosses}"


if __name__ == "__main__":
    if not hc_available():
        print("SKIP: hc CLI not found at ~/.dotnet/tools/hc.exe")
        raise SystemExit(0)
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
