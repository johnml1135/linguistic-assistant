"""Tests for HC-parsed morpheme alignment. The pure pieces (segmentation from the gloss line, marker
assembly, accept/defer routing) run fully offline; the end-to-end run is gated on `hc` + THOT."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from align import morph_align_hc as M  # noqa: E402
from align.contract import CandidateGloss, GlossTable  # noqa: E402
from golden.grammar import Affix, LangModel, LexEntry  # noqa: E402

# a tiny Swahili-style grammar: ni-na-ku-penda = I-PRES-you-love
MODEL = LangModel(code="swh", lexicon=[LexEntry(form="penda", gloss="love", pos="Verb", count=9)],
                  affixes=[Affix(form="ni", gloss="I", kind="prefix", count=5, slot_ord=4),
                           Affix(form="na", gloss="PRES", kind="prefix", count=5, slot_ord=3),
                           Affix(form="ku", gloss="you", kind="prefix", count=5, slot_ord=2)])
IDX = M.gloss_index(MODEL)


def test_gloss_index_maps_constructs():
    assert IDX["love"] == ("penda", "root", 0)
    assert IDX["you"] == ("ku", "prefix", 2)
    assert IDX["I"][1] == "prefix"


def test_morphemes_of_recovers_root_by_peeling():
    morphs = M.morphemes_of("ninakupenda", ("I", "PRES", "you", "love"), IDX)
    assert [m["type"] for m in morphs] == ["prefix", "prefix", "prefix", "root"]
    assert [m["form"] for m in morphs] == ["ni", "na", "ku", "penda"]   # root peeled to 'penda'
    assert [m["gloss"] for m in morphs] == ["I", "PRES", "you", "love"]


def test_morphemes_of_unmapped_gloss_keeps_word():
    morphs = M.morphemes_of("xyz", ("NOPE",), IDX)
    assert len(morphs) == 1 and morphs[0]["type"] == "word" and morphs[0]["unmapped"]


def test_word_morphemes_unparsed_and_ambiguous():
    assert M.word_morphemes("zzz", [], IDX)[0]["unparsed"] is True
    morphs = M.word_morphemes("ninakupenda", [("I", "PRES", "you", "love"), ("I", "PRES", "love")], IDX)
    assert all(m.get("ambiguous") for m in morphs)


def test_agrees_root_and_affix():
    assert M._agrees("root", "love", "love") is True
    assert M._agrees("prefix", "you (2SG.OBJ)", "you") is True
    assert M._agrees("prefix", "PRES", "you") is False        # function morpheme, no overlap → defer
    assert M._agrees("root", "love", "") is False


def _table(**pairs) -> GlossTable:
    return GlossTable(table={
        form: [CandidateGloss(target_word=form, source_word=sw, prob=p, count=3)]
        for form, (sw, p) in pairs.items()})


def test_assemble_and_route_accept_defer():
    streams = [("MAT 1:1", 0, [
        {"form": "penda", "gloss": "love", "type": "root", "slot": 0, "_word": "ninakupenda"},
        {"form": "ku", "gloss": "you", "type": "prefix", "slot": 2, "_word": "ninakupenda"},
        {"form": "na", "gloss": "PRES", "type": "prefix", "slot": 3, "_word": "ninakupenda"},
    ])]
    table = _table(penda=("love", 0.92), ku=("you", 0.80), na=("the", 0.30))
    affix_feats = {"ku": {"Person": "2", "Number": "Sing", "Case": "Obj"}}
    markers = M.assemble_markers(streams, table, affix_feats, pos_of={"penda": "Verb"})
    by_form = {m.form: m for m in markers}
    # root with a concurring high-prob content gloss → accept, POS attached
    assert by_form["penda"].decision == "accept" and by_form["penda"].pos == "Verb"
    # object suffix aligns to "you", agrees, high prob → accept, features attached
    assert by_form["ku"].decision == "accept" and by_form["ku"].features.get("Case") == "Obj"
    # 'na' (PRES) aligned to "the" weakly and disagrees → defer (no silent wrong marker)
    assert by_form["na"].decision == "defer"


def test_unparsed_marker_never_accepts():
    streams = [("X", 0, [{"form": "zzz", "gloss": "?", "type": "word", "slot": 0,
                          "unparsed": True, "_word": "zzz"}])]
    table = _table(zzz=("whatever", 0.99))
    m = M.assemble_markers(streams, table, {})[0]
    assert m.decision == "defer" and m.flags.get("unparsed")


def test_to_deferral_records_bridge():
    deferred = [
        M.MorphMarker(verse="X", word="w", word_idx=0, morph_idx=0, form="root1", gloss="?",
                      type="root", confidence=0.4, source_tokens=[("dog", 0.4)], decision="defer"),
        M.MorphMarker(verse="X", word="w", word_idx=0, morph_idx=1, form="ku", gloss="you",
                      type="prefix", confidence=0.45, source_tokens=[("you", 0.45)],
                      features={"Person": "2"}, decision="defer"),
        M.MorphMarker(verse="X", word="z", word_idx=1, morph_idx=0, form="z", gloss="?", type="word",
                      confidence=0.9, source_tokens=[("x", 0.9)], decision="defer", flags={"unparsed": True}),
    ]
    recs = M.to_deferral_records(deferred, top=10)
    assert any(r.get("word") == "root1" for r in recs)          # root → lexeme_gloss deferral
    assert any(r.get("affix") == "ku" for r in recs)            # affix → affix_function deferral
    assert all("unparsed" not in str(r) for r in recs)          # unparsed markers are not ticketed
    # the records are exactly the shape deferrals.build consumes
    from deferrals.build import build_ticket
    t = build_ticket("spa", next(r for r in recs if r.get("word")), with_counterfactuals=False)
    t.validate()


@pytest.mark.skipif(not (_RESEARCH / "golden").exists(), reason="golden data absent")
def test_run_cooccur_offline_if_hc_available():
    from golden.reference.hc_coverage import hc_available
    if not hc_available():
        pytest.skip("hc CLI not installed")
    s = M.run("spa", backend="cooccur", sample=40)        # cooccur backend: no THOT needed
    assert s["markers"] >= 1 and s["accepted"] + s["deferred"] == s["markers"]
    assert s["backend"] == "cooccur"
