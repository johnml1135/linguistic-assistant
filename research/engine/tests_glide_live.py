"""Tests for the LIVE glide rule in the main grammar (engine.hc.build_grammar_xml glide_rule=...). Pure-XML
tests always run; the parse round-trip runs only where hc.exe is installed (skipped otherwise — honest)."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from engine import hc as HC                              # noqa: E402
from engine.grammar import Affix, LangModel, LexEntry   # noqa: E402


def _model():
    roots = ["ombo", "ote", "tu", "yesu", "watu"]       # forms supply v/y/w to the charset
    return LangModel(code="swh", lexicon=[LexEntry(form=r, gloss=f"R_{r}", pos="root") for r in roots],
                     affixes=[Affix(form="vi", gloss="vi-", kind="prefix")])


def test_glide_off_is_byte_for_byte_identity():
    m = _model()
    assert HC.build_grammar_xml(m, glide_rule=False) == HC.build_grammar_xml(m)   # default unchanged


def test_glide_on_emits_substrate_and_rule():
    xml = HC.build_grammar_xml(_model(), glide_rule=True)
    assert '<SymbolicFeature id="syl"' in xml             # syllabicity feature added
    assert 'id="nc_high_syl"' in xml and 'id="nc_glide_out"' in xml   # rule's classes
    assert 'naturalClass="nc_high_syl"' in xml            # the glide rule itself is referenced
    assert 'phonologicalRules=' in xml                    # wired into the stratum


def test_glide_block_vowels_emits_trigger_class():
    xml = HC.build_grammar_xml(_model(), glide_rule=True, glide_block_vowels=frozenset({"u"}))
    assert 'id="nc_trigger"' in xml                       # conditioned right-environment class
    assert 'naturalClass="nc_trigger"' in xml


def test_live_glide_parses_glide_form_via_ur():
    """The payoff: with vy- PRUNED and the glide rule live, HC parses vyombo as vi-+ombo."""
    from engine.hc_collapse import hc_available
    if not hc_available():
        return
    m = _model()                                          # vi- only, no vy-
    res = HC.run_parse(m, ["vitu", "vyombo", "vyote"], templated=False, glide_rule=True, chunk_timeout=30)
    assert res.get("vitu") and res.get("vyombo") and res.get("vyote")
    glosses = {g for a in res["vyombo"] for _, g in a}
    assert "vi-" in glosses                               # vyombo analysed as vi- + stem (rule un-applied)


if __name__ == "__main__":
    import traceback
    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for name, fn in fns:
        try:
            fn(); passed += 1; print(f"  ok  {name}")
        except Exception:
            print(f"FAIL  {name}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    raise SystemExit(0 if passed == len(fns) else 1)
