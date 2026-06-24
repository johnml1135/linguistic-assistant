"""Tests for the glide-collapse emitter + HC round-trip gate. Pure-XML tests always run; the round-trip
tests run only where hc.exe is installed (skipped otherwise — honest, not a false pass)."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from engine import hc_collapse as HC   # noqa: E402


# ── pure: the emitter + grammar inventory ───────────────────────────────────────────────────────────────
def test_glide_rule_xml_shape():
    rid, xml = HC.glide_rule_xml()
    assert rid == "r_glide"
    assert 'naturalClass="nc_high_syl"' in xml          # input: high syllabic vowel
    assert 'naturalClass="nc_glide_out"' in xml         # output: nonsyllabic
    assert "RightEnvironment" in xml and 'naturalClass="nc_syl"' in xml   # before a vowel


def test_segment_defs_glide_is_nonsyllabic_twin():
    defs, _cids = HC._segment_defs({"u", "w", "a", "m"})
    assert 's_w' in defs and 'symbolValues="minus"' in defs   # w = [-syl]
    assert 's_u' in defs and 'symbolValues="plus"' in defs    # u = [+syl]


def test_build_grammar_auto_adds_glide_segment():
    # the glide 'w' only appears in surface members, never in the stems — the builder must add it
    xml = HC.build_collapse_grammar("mu", [("ana", "ST0"), ("ngu", "ST1")])
    assert "<Representation>w</Representation>" in xml
    assert 'phonologicalRules="r_glide"' in xml


def test_glide_of_table():
    assert HC.GLIDE_OF == {"u": "w", "i": "y"}


# ── HC-gated: the actual round-trip ─────────────────────────────────────────────────────────────────────
def test_round_trip_clean_when_no_counterexamples():
    if not HC.hc_available():
        print("  (skip: hc.exe not installed)"); return
    # only mu+consonant + mw+vowel (no falsifying mu+vowel word) → no exceptions in-environment
    r = HC.glide_collapse_round_trips("mu", "u", "w", ["mungu", "muda"], ["mwana", "mwili"])
    assert r["ran"] is True and r["recall_env"] == 1.0 and r["n_exceptions"] == 0


def test_round_trip_catches_counterexample():
    if not HC.hc_available():
        print("  (skip: hc.exe not installed)"); return
    # muumini = mu+umini keeps mu before a vowel — the rule u->w over-applies, so it must be flagged
    r = HC.glide_collapse_round_trips("mu", "u", "w", ["mungu", "muumini"], ["mwana", "mwili"])
    assert r["n_exceptions"] >= 1 and "muumini" in r["failures"]   # the falsifying case is caught


def test_round_trip_rejects_bad_ur():
    r = HC.glide_collapse_round_trips("ma", "u", "w", ["mungu"], ["mwana"])
    assert r["ok"] is False and "does not end" in r["reason"]      # ur must end in the alternating vowel


def test_round_trip_needs_both_environments():
    r = HC.glide_collapse_round_trips("mu", "u", "w", ["mungu"], [])
    assert r["ok"] is False                                        # no glide-env members → can't validate


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
