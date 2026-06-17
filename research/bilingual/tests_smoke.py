"""Offline smoke tests for the Apertium-alignment bridge. Run: `python research/bilingual/tests_smoke.py`
(also pytest-discoverable). No Apertium binary, no HC, no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bilingual.bidix import parse_bidix, serialize_bidix  # noqa: E402
from bilingual.crosswalk import Crosswalk  # noqa: E402
from bilingual.fixtures import (  # noqa: E402
    fixture_bidix,
    fixture_source_tokens,
    fixture_target_tokens,
)
from bilingual.finder import find_reference  # noqa: E402
from bilingual.qa import assess  # noqa: E402
from bilingual.sense_links import build_bidix, from_change_set  # noqa: E402
from bilingual.stream import hc_analysis_to_token, parse_stream, render_stream  # noqa: E402
from proposal.change_set import validate_change_set  # noqa: E402
from proposal.contract import ChangeSet  # noqa: E402


def test_stream_round_trip():
    s = "^wachungaji/mchungaji<n><pl>$ ^kondoo/kondoo<n><pl>$"
    assert render_stream(parse_stream(s)) == s


def test_crosswalk_maps_and_reports_unmapped():
    cw = Crosswalk()
    mapped, unmapped = cw.to_apertium(["Noun", "pl", "Mystery"])
    assert mapped == ["n", "pl"] and unmapped == ["Mystery"]
    tok, un = hc_analysis_to_token("wachungaji", "mchungaji", ["Noun", "pl"], cw)
    assert tok.analyses[0].tags == ("n", "pl") and un == []


def test_bidix_dix_round_trip():
    b = fixture_bidix()
    again = parse_bidix(serialize_bidix(b))
    assert sorted((e.reference, e.vernacular) for e in again.entries) == sorted(
        (e.reference, e.vernacular) for e in b.entries
    )


def test_finder_locates_under_reorder_and_reports_missing():
    b, tgt = fixture_bidix(), fixture_target_tokens()
    corr = find_reference("shepherd", tgt, b)  # target is verb-first; shepherd is 2nd
    assert corr.found and corr.matches[0].lemma == "mchungaji" and corr.matches[0].target_index == 1
    assert find_reference("love", tgt, b).found is False  # not in bidix → missing


def test_qa_flags_are_deterministic_and_expected():
    src, tgt, b = fixture_source_tokens(), fixture_target_tokens(), fixture_bidix()
    flags = assess(src, tgt, b)
    kinds = sorted((f.kind, f.source_lemma) for f in flags)
    assert kinds == [("agreement_mismatch", "sheep"), ("missing_concept", "love")]
    assert all(f.review_only for f in flags)
    assert [(f.kind, f.source_lemma) for f in assess(src, tgt, b)] == [
        (f.kind, f.source_lemma) for f in flags
    ]  # reproducible


def test_sense_links_build_bidix_from_validated_change_set():
    text = (
        '{"ops":[{"op":"bilingual.sense_link.add",'
        '"vernacular_sense":{"entry":"mchungaji","sense":1,"pos":"Noun"},'
        '"reference_lemma":{"lang":"eng","lemma":"shepherd","pos":"Noun"},'
        '"confidence":0.7}]}'
    )
    cs = validate_change_set(text)
    assert isinstance(cs, ChangeSet)
    links = from_change_set(cs.ops)
    bidix = build_bidix(links)
    assert bidix.lookup_by_reference("shepherd") == [("mchungaji", ("n",))]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
