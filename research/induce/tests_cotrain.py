"""Offline tests for the THOT<->HC co-training loop. HC parsing, THOT alignment, and freqs are mocked so
the loop's control logic is tested without a corpus/parser: proposal gating (content vs function word,
probability), coverage-guard (keep only if coverage rises), and fixpoint stop."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from engine.grammar import LangModel, LexEntry   # noqa: E402
from induce import cotrain as CT                  # noqa: E402


class _Best:
    def __init__(self, source_word, prob):
        self.source_word, self.prob = source_word, prob


class _Table:
    def __init__(self, m):
        self.m = m

    def best(self, form):
        return self.m.get(form)


def test_propose_roots_gates_content_vs_function(monkeypatch):
    monkeypatch.setattr(CT.langknow, "function_words", lambda lang: {"and", "of", "the"})
    table = _Table({
        "mkate": _Best("bread", 0.8),     # content, high prob -> propose
        "wa": _Best("of", 0.9),           # function word -> reject (grammatical, an affix's job)
        "x": _Best("dog", 0.3),           # below gate -> reject
        "y": _Best("ox", 0.9),            # source too short (<3) -> reject
        "enzi": _Best("throne", 1.0),     # content -> propose
    })
    out = CT.propose_roots(["mkate", "wa", "x", "y", "enzi", "known"], table,
                           gate=0.5, known_forms={"known"})
    assert set(out) == {"mkate", "enzi"}
    assert out["mkate"][0] == "bread" and out["mkate"][1] == 0.8 and out["enzi"][0] == "throne"
    assert out["mkate"][2] == ("mkate",)        # source words tracked (for round-trip)


def test_propose_roots_strips_affixes_to_generalise(monkeypatch):
    monkeypatch.setattr(CT.langknow, "function_words", lambda lang: set())
    # two inflected forms of the same root 'penda' (love): wa-penda, a-penda-na
    table = _Table({"wapenda": _Best("love", 0.9), "apendana": _Best("love", 0.8)})
    out = CT.propose_roots(["wapenda", "apendana"], table, gate=0.5,
                           prefixes=["wa", "a"], suffixes=["na"])
    # both inflected forms strip to the shared root 'penda' -> ONE generalising root, not two whole words
    assert "penda" in out
    assert "wapenda" not in out and "apendana" not in out
    assert out["penda"][0] == "love"


def test_residue_peels_one_prefix_and_one_suffix():
    assert CT._residue("wapendana", ["wa", "a"], ["na"]) == "pendan" or \
           CT._residue("wapendana", ["wa"], ["na"]) == "penda"     # wa- + -na peeled
    assert CT._residue("mtu", ["m"], []) == "tu"                   # one prefix
    assert CT._residue("xy", ["x"], []) == "xy"                    # too short to strip (residue<2)


def _model():
    return LangModel(code="xx", lexicon=[LexEntry(form="root1", gloss="r", pos="root", count=1)], affixes=[])


def test_cotrain_adds_roots_and_is_coverage_guarded(monkeypatch):
    # words: two unparsed content words that THOT can gloss; coverage rises as roots are added then plateaus
    WORDS = ["root1", "mkate", "enzi"]
    monkeypatch.setattr(CT.langknow, "function_words", lambda lang: set())
    monkeypatch.setattr(CT, "_align_table", lambda pair, model, sample, **kw: _Table(
        {"mkate": _Best("bread", 0.9), "enzi": _Best("throne", 0.9)}))
    monkeypatch.setattr("induce.tdd.load_freqs", lambda pair: __import__("collections").Counter(
        {"root1": 5, "mkate": 4, "enzi": 3}))
    monkeypatch.setattr("gold.phonology_gold.phon_feats", lambda pair, charset: {})

    # HC parses exactly the roots currently in the model (so adding a root makes that word parse)
    def fake_run_parse(model, words, **kw):
        forms = {e.form for e in model.lexicon}
        return {w: [("x",)] if w in forms else [] for w in words}

    monkeypatch.setattr("engine.hc.run_parse", fake_run_parse)

    r = CT.cotrain("xx", cycles=5, sample=10, words=WORDS, start=_model(), verbose=False)
    forms = {e.form for e in r["model"].lexicon}
    assert "mkate" in forms and "enzi" in forms                 # THOT-glossed roots were added
    assert r["final_coverage"] == 1.0                            # all three now parse
    assert r["roots_added"] == 2
    # last recorded cycle must be a kept (coverage-improving) one or the fixpoint break
    assert all(row["kept"] for row in r["history"])             # guard never kept a non-improving cycle


def test_roundtrip_drops_roots_that_dont_reparse(monkeypatch):
    """(switch a) A proposed root is kept only if it lets HC re-parse a source word; one that doesn't is
    dropped even though THOT proposed it."""
    base = _model()
    proposals = {
        "good": ("dog", 0.9, ("goodword",)),    # source 'goodword' WILL parse once 'good' is a root
        "bad": ("cat", 0.9, ("badword",)),      # source 'badword' will NOT parse -> dropped
    }

    def fake_run_parse(model, words, **kw):
        forms = {e.form for e in model.lexicon}
        return {w: ([("x",)] if (w == "goodword" and "good" in forms) else []) for w in words}

    monkeypatch.setattr("engine.hc.run_parse", fake_run_parse)
    kept = CT._roundtrip_keep(base, proposals, pf={})
    assert set(kept) == {"good"}                 # 'bad' dropped: no source word re-parsed


def test_reuse_table_aligns_once(monkeypatch):
    """(switch c) reuse_table computes the THOT table a single time and reuses it across cycles."""
    WORDS = ["root1", "mkate", "enzi"]
    calls = {"n": 0}
    monkeypatch.setattr(CT.langknow, "function_words", lambda lang: set())

    def fake_align(pair, model, sample, **kw):
        calls["n"] += 1
        return _Table({"mkate": _Best("bread", 0.9), "enzi": _Best("throne", 0.9)})

    monkeypatch.setattr(CT, "_align_table", fake_align)
    monkeypatch.setattr("induce.tdd.load_freqs", lambda pair: __import__("collections").Counter(
        {"root1": 5, "mkate": 4, "enzi": 3}))
    monkeypatch.setattr("gold.phonology_gold.phon_feats", lambda pair, charset: {})
    monkeypatch.setattr("engine.hc.run_parse",
                        lambda model, words, **kw: {w: ([("x",)] if w in {e.form for e in model.lexicon} else [])
                                                    for w in words})
    CT.cotrain("xx", cycles=3, words=WORDS, start=_model(), reuse_table=True, verbose=False)
    assert calls["n"] == 1                        # aligned once, reused thereafter


def test_cotrain_stops_when_no_proposals(monkeypatch):
    WORDS = ["root1", "junk"]
    monkeypatch.setattr(CT.langknow, "function_words", lambda lang: set())
    monkeypatch.setattr(CT, "_align_table", lambda pair, model, sample, **kw: _Table({}))  # THOT offers nothing
    monkeypatch.setattr("induce.tdd.load_freqs", lambda pair: __import__("collections").Counter(
        {"root1": 5, "junk": 1}))
    monkeypatch.setattr("gold.phonology_gold.phon_feats", lambda pair, charset: {})
    monkeypatch.setattr("engine.hc.run_parse",
                        lambda model, words, **kw: {w: ([("x",)] if w == "root1" else []) for w in words})
    r = CT.cotrain("xx", cycles=5, sample=10, words=WORDS, start=_model(), verbose=False)
    assert r["roots_added"] == 0 and r["cycles_run"] == 0       # no confident proposals -> immediate fixpoint


if __name__ == "__main__":
    import traceback

    class _MP:
        def setattr(self, obj, name, val=None):
            if val is None and isinstance(obj, str):
                mod, _, attr = obj.rpartition(".")
                import importlib
                setattr(importlib.import_module(mod), attr, name)
            else:
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
