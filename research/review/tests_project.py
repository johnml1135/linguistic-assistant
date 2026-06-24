"""Offline tests for cross-lingual projection: role projection through a (fake) alignment, the PROPN
filter (the Matthew-1 names guard), and subject-marker extraction. No parser/corpus needed."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import project as PJ   # noqa: E402


class _Best:
    def __init__(self, s):
        self.source_word = s


class _Table:
    def __init__(self, m):
        self.m = m

    def best(self, w):
        return _Best(self.m[w]) if w in self.m else None


def test_subject_marker_extraction():
    assert PJ.subject_marker("anasoma") == "a"        # cl1 SM
    assert PJ.subject_marker("wanasoma") == "wa"      # cl2 SM
    assert PJ.subject_marker("unasoma") == "u"        # cl3/11 SM
    assert PJ.subject_marker("ki") is not None


def test_project_verse_roles_and_propn_skip():
    # pivot: "the man sees john" — man=nsubj of sees; john=PROPN nsubj (a name) → must be skipped
    toks = [(0, "the", "DET", "det", 1), (1, "man", "NOUN", "nsubj", 2),
            (2, "sees", "VERB", "ROOT", 2), (3, "john", "PROPN", "nsubj", 2)]
    table = _Table({"mtu": "man", "anaona": "sees", "yohana": "john"})
    proj = PJ.project_verse(toks, [], ["mtu", "anaona", "yohana"], table)
    by = {p["vern"]: p for p in proj}
    assert by["mtu"]["role"] == "nsubj" and by["mtu"]["head_vern"] == "anaona"
    assert "yohana" not in by                          # PROPN name not projected (Matthew-1 guard)


def test_project_verse_ignores_unaligned():
    toks = [(0, "man", "NOUN", "nsubj", 1), (1, "runs", "VERB", "ROOT", 1)]
    proj = PJ.project_verse(toks, [], ["xyz"], _Table({}))   # xyz aligns to nothing
    assert proj == []


def test_classify_by_subject_marking_splits_m_ambiguity(monkeypatch):
    # mwana (child) takes a- → cl1; mkono (hand) takes u- → cl3 — the split nothing else can make
    pairs = [("mwana", "anasoma"), ("mwana", "anakuja"), ("mkono", "unauma"), ("mkono", "ulivunjika"),
             ("watu", "wanakuja"), ("watu", "walikuja")]
    monkeypatch.setattr(PJ, "subject_verb_pairs", lambda pair, pivot="en", sample=0: pairs)
    cl = PJ.classify_by_subject_marking("swh")
    assert cl["mwana"]["class"] == "1" and cl["mkono"]["class"] == "3" and cl["watu"]["class"] == "2"


def test_word_order_computes_svo(monkeypatch):
    toks = [(0, "man", "NOUN", "nsubj", 1, {}), (1, "sees", "VERB", "root", 1, {}),
            (2, "house", "NOUN", "obj", 1, {})]
    monkeypatch.setattr(PJ, "get_parser", lambda pivot="en", backend="auto": (lambda s: toks))
    monkeypatch.setattr(PJ, "_word_alignment", lambda pair, sample: (
        [("R", ["man", "sees", "house"], ["mtu", "ona", "nyumba"])],
        _Table({"mtu": "man", "ona": "sees", "nyumba": "house"})))
    assert PJ.word_order("swh")["dominant"] == "SVO"      # mtu(0) ona(1) nyumba(2) → S V O


def test_label_tam_derives_tense_from_pivot(monkeypatch):
    toks = [(0, "walked", "VERB", "root", 0, {"Tense": "Past"})]
    monkeypatch.setattr(PJ, "get_parser", lambda pivot="en", backend="auto": (lambda s: toks))
    monkeypatch.setattr(PJ, "_word_alignment", lambda pair, sample: (
        [("R", ["walked"], ["alitembea"])] * 8, _Table({"alitembea": "walked"})))
    # alitembea → SM 'a', rest 'litembea', TAM slot 'li' ← derived as Past from the English Tense feature
    assert PJ.label_tam("swh", min_count=1)["derived_tam_labels"].get("li", {}).get("tense") == "Past"


def test_induce_tam_finds_known_swahili_markers():
    r = PJ.induce_tam("swh")
    hits = {f["marker"] for f in r["known_hits"]}
    assert {"li", "na", "ta", "me"} <= hits          # past/present/future/perfect — the core TAM markers


def test_subject_number_agreement_separates_sg_pl(monkeypatch):
    pairs = [("hombre", "dijo"), ("hombre", "vino"), ("hombres", "dijeron"), ("hombres", "vinieron")]
    monkeypatch.setattr(PJ, "subject_verb_pairs", lambda pair, pivot="en", sample=0: pairs)
    r = PJ.subject_number_agreement("spa", min_count=1)
    pl = {s for s, _ in r["plural_subject_endings"]}
    assert "on" in pl                                 # plural subjects → 3pl '-ron/- on' endings


if __name__ == "__main__":
    import traceback

    class _MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for name, fn in fns:
        try:
            fn(_MP()) if "monkeypatch" in fn.__code__.co_varnames else fn()
            passed += 1; print(f"  ok  {name}")
        except Exception:
            print(f"FAIL  {name}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    raise SystemExit(0 if passed == len(fns) else 1)
