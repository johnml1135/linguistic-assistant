"""Offline smoke tests for the reference-gold parsers (fixtures; no network)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from golden.reference.build import _parse_ud, _parse_unimorph  # noqa: E402
from golden.reference.sources import POS_TO_UPOS  # noqa: E402

_UNIMORPH = "casa\tcasas\tN;PL\ncasa\tcasa\tN;SG\nhablar\thablé\tV;PST;1;SG\n"
_UD = (
    "# sent_id = 1\n"
    "1\tLa\tel\tDET\t_\t_\t2\tdet\t_\t_\n"
    "2\tcasa\tcasa\tNOUN\t_\t_\t0\troot\t_\t_\n"
    "3-4\tdel\t_\t_\t_\t_\t_\t_\t_\t_\n"   # multiword token — must be skipped
    "3\tde\tde\tADP\t_\t_\t2\tcase\t_\t_\n"
    "\n"
)


def test_parse_unimorph_collects_lemmas_forms_features():
    d = _parse_unimorph(_UNIMORPH)
    assert "casa" in d["lemmas"] and "hablar" in d["lemmas"]
    assert "casas" in d["forms"] and "hablé" in d["forms"]
    assert "N;PL" in d["features"]


def test_parse_ud_form_to_upos_skips_multiword():
    d = _parse_ud(_UD)
    assert d["pos_by_form"]["casa"] == "NOUN"
    assert d["pos_by_form"]["la"] == "DET"
    assert "del" not in d["pos_by_form"]  # the 3-4 multiword token row is skipped
    assert "casa" in d["lemmas"]


def test_pos_to_upos_covers_cycle_pos_ids():
    for pid in ("noun", "verb", "adj", "adv", "pron", "prep", "conj", "det", "num", "ptcl"):
        assert pid in POS_TO_UPOS


def test_unimorph_pos_conversion():
    from golden.reference.compile import unimorph_pos
    assert unimorph_pos("N;PL") == "NOUN"
    assert unimorph_pos("V;IND;PST;1;SG") == "VERB"
    assert unimorph_pos("ADJ;FEM;PL") == "ADJ"


def test_segment_finds_suffix_prefix_and_replacive():
    from golden.reference.compile import segment
    assert segment("casa", "casas") == ("suffix", "s")          # suffixing
    assert segment("soma", "ninasoma") == ("prefix", "nina")    # prefixing
    assert segment("hablar", "hablé") == ("suffix", "é")        # replacive ending (shared stem 'habl')
    assert segment("casa", "casa") is None                       # no change → no affix


def test_liblcm_converters_map_to_destination_terms():
    import liblcm
    assert liblcm.pos_from_upos("NOUN") == "Noun" and liblcm.pos_from_upos("SCONJ") == "Subordinating connective"
    assert liblcm.pos_from_cycle("prep") == "Adposition"
    assert liblcm.pos_from_wiktionary("name") == "Proper noun" and liblcm.pos_from_wiktionary("verb") == "Verb"
    assert liblcm.inflection_features("V;IND;PST;1;SG") == {
        "Mood": "Indicative", "Tense": "Past", "Person": "First", "Number": "Singular"}


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
