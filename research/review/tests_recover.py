"""Offline test for recovery: the SM→class map is DERIVED from data (anchored on noun classes + projected
subjects), not read from the hardcoded constant. Mocked so it runs without a parser/corpus."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import recover as R   # noqa: E402


def test_langknow_no_hardcoded_leakage():
    """The core guarantee: the algorithm carries NO hardcoded linguistic knowledge — it loads per-language
    reference data (review.langknow) from golden_sets/_reference/<lang>.json. swh (Bantu) has reference data;
    an UNKNOWN language gets {} from every accessor, so no Bantu/Spanish facts leak into its analysis — the
    engine then runs purely on what projection + concord derive."""
    from review import langknow
    assert langknow.noun_class_prefixes("swh").get("ki") == "7"        # swh reference present
    assert langknow.subject_marker_to_class("swh").get("a") == "1"
    assert langknow.masculine_articles("spa") == {"el", "los", "un", "unos"}
    # unknown language → every accessor empty (no leakage)
    for acc in (langknow.noun_class_prefixes, langknow.subject_marker_to_class, langknow.tam_markers,
                langknow.associative_to_class, langknow.masculine_articles, langknow.class_prefix_set,
                langknow.object_markers, langknow.subject_markers, langknow.meinhof_inventory):
        assert not acc("qqq"), f"{acc.__name__} leaked knowledge for an unknown language"


def test_derive_class_pairs_from_distribution(monkeypatch):
    """The sg/pl number-pairing surfaces the real class pairings (m·wa, ki·vi) from pure distribution —
    no hardcoded prefix list — and the strongest pairing wins. Mocked corpus."""
    from gold import goldio
    from review import project as PJ
    # a toy noun lexicon with clean sg/pl alternations: m/wa (people) and ki/vi (things)
    sg_pl = {f"m{s}": "noun" for s in ["tu", "ke", "zee", "toto", "geni", "limu"]}
    sg_pl.update({f"wa{s}": "noun" for s in ["tu", "ke", "zee", "toto", "geni", "limu"]})
    sg_pl.update({f"ki{s}": "noun" for s in ["tu", "kapu", "ti", "tabu", "su"]})
    sg_pl.update({f"vi{s}": "noun" for s in ["tu", "kapu", "ti", "tabu", "su"]})
    monkeypatch.setattr(goldio, "load_gold", lambda pair: {"pos": sg_pl})
    monkeypatch.setattr(PJ, "load_pos", lambda pair: {})
    pairs = R.derive_class_pairs("swh", min_stems=4, min_pair=4)
    got = {tuple(d["prefixes"]) for d in pairs}
    assert ("m", "wa") in got                       # cl1/2 pairing recovered from distribution
    assert ("ki", "vi") in got                      # cl7/8 pairing recovered
    assert pairs[0]["prefixes"] == ["m", "wa"]       # strongest pairing wins


def test_noun_class_map_ceiling(monkeypatch):
    """Documents the MEASURED CEILING: prefix→class is derivable from concord ONLY for classes whose nouns
    control agreement (people, cl1/2). Inanimate classes (cl4/5/7/8) rarely head a subject or take
    associative concord in the NT, so their prefix→class can't be derived — which is exactly why the
    noun-class prefix→class map lives as per-language reference data (review.langknow). Mocked, runs offline."""
    from review import recover as RR
    # derived inventory includes both animate (wa) and inanimate (ki, vi, ma) prefixes
    monkeypatch.setattr(RR, "derive_prefixes", lambda pair, **kw: {"wa": {}, "ki": {}, "vi": {}, "ma": {}})
    # but concord only SEES the animate ones as subjects/controllers (the corpus reality)
    anchor = {f"wa{s}": "2" for s in ["tu", "ke", "zee", "toto", "geni", "limu"]}
    monkeypatch.setattr(RR, "_concord_anchored_classes", lambda pair, sample=0: anchor)
    m = RR.derive_noun_class_map("swh", min_support=4)
    assert m.get("wa", {}).get("class") == "2"          # animate class recovered from concord
    assert "ki" not in m and "vi" not in m and "ma" not in m   # inanimate classes NOT recoverable — the ceiling


def test_derive_sm_to_class_from_data(monkeypatch):
    from review import classes as CL
    from review import project as PJ
    # noun classes (the anchor) + projected subject-verb pairs → derive SM→class WITHOUT SM_TO_CLASS
    monkeypatch.setattr(CL, "persisted_noun_classes",
                        lambda pair: {"mtu": {"class": "1"}, "watu": {"class": "2"}, "kitu": {"class": "7"}})
    pairs = [("mtu", "anasoma"), ("mtu", "anakuja"), ("watu", "wanasoma"), ("watu", "wanakuja"),
             ("kitu", "kinaanguka"), ("kitu", "kilianguka")]
    monkeypatch.setattr(PJ, "subject_verb_pairs", lambda pair, pivot="en", sample=0: pairs)
    d = R.derive_sm_to_class("swh", min_count=2)
    assert d.get("a") == "1" and d.get("wa") == "2" and d.get("ki") == "7"   # recovered from data


if __name__ == "__main__":
    import traceback

    class _MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for name, fn in fns:
        try:
            fn(_MP()); passed += 1; print(f"  ok  {name}")
        except Exception:
            print(f"FAIL  {name}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    raise SystemExit(0 if passed == len(fns) else 1)
