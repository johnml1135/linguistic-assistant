"""Offline tests for the explore tools: noun browsing, ranked class hypotheses + fit-none, and the residue
pattern-finder. Corpus/gold/derivation are mocked so the logic runs without data."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import explore as EX   # noqa: E402


def test_noun_entries_filters_and_shows_signals(monkeypatch):
    monkeypatch.setattr(EX, "_nouns", lambda pair: {"mtu", "watu", "kitu", "vyombo"})
    monkeypatch.setattr(EX, "_freqs", lambda pair: Counter({"mtu": 9, "watu": 8, "kitu": 5, "vyombo": 2}))
    monkeypatch.setattr("review.classes.persisted_noun_classes",
                        lambda pair: {"mtu": {"class": "1", "source": "subject-marking", "confidence": 0.9}})
    monkeypatch.setattr("review.langknow.class_prefix_set", lambda lang: ["wa", "ki", "vy", "m"])
    r = EX.noun_entries("swh", "^wa", limit=10)
    assert r["n_nouns"] == 4 and r["n_matched"] == 1            # only watu matches ^wa
    assert r["rows"][0]["noun"] == "watu" and r["rows"][0]["prefix"] == "wa"
    full = EX.noun_entries("swh", "", limit=10)
    assert full["n_classified"] == 1                            # mtu classified
    assert next(x for x in full["rows"] if x["noun"] == "mtu")["class"] == "1"


def test_class_hypotheses_ranked_with_fit_none(monkeypatch):
    monkeypatch.setattr(EX, "_nouns", lambda pair: {"mtu", "watu", "kitu", "vitu", "ndege", "siku"})
    monkeypatch.setattr(EX, "_freqs", lambda pair: Counter())
    monkeypatch.setattr("review.recover.emergent_class_groups",
                        lambda pair, top=8: [{"prefixes": ["ki", "vi"]}, {"prefixes": ["m", "wa"]}])
    r = EX.class_hypotheses("swh")
    # ki/vi explains kitu,vitu (2); m/wa explains mtu,watu (2); ndege,siku fit none
    by = {h["label"]: h for h in r["hypotheses"]}
    assert by["ki/vi- class"]["n_explained"] == 2 and by["m/wa- class"]["n_explained"] == 2
    assert all("rank" in h for h in r["hypotheses"])
    assert r["fit_none"]["n"] == 2 and set(r["fit_none"]["examples"]) == {"ndege", "siku"}


def test_residue_patterns_finds_recurring_substrings(monkeypatch):
    # unexplained nouns (no class / cl9-10): several share the initial 'ki' and the final 'ni'
    nouns = {"kitabu", "kileo", "kilima", "mtoni", "ziwani", "shambani", "rafiki"}
    monkeypatch.setattr(EX, "_nouns", lambda pair: nouns)
    monkeypatch.setattr(EX, "_freqs", lambda pair: Counter())
    monkeypatch.setattr("review.classes.persisted_noun_classes",
                        lambda pair: {"rafiki": {"class": "9/10"}})   # rafiki still residue (cl9/10 default)
    r = EX.residue_patterns("swh", min_cluster=3)
    pats = {(p["lens"], p["pattern"]) for p in r["patterns"]}
    assert ("initial 2 chars", "ki") in pats                   # kitabu/kileo/kilima
    assert ("final 2 chars", "ni") in pats                     # mtoni/ziwani/shambani


def test_apply_residue_pattern_gated_closes_loop(monkeypatch):
    """The stem-recurrence GATE assigns genuine affixed nouns (nyumba-ni: nyumba recurs) but SKIPS
    coincidental endings (amini: no 'ami' stem) — then the residue shrinks by the gated count."""
    nouns = {"mbinguni", "nyumbani", "duniani", "amini", "mtu", "kazi"}
    freqs = Counter({"mbingu": 9, "nyumba": 12, "dunia": 15})   # stems that recur; 'ami' absent → amini skipped
    store = {"mtu": {"class": "1"}}
    monkeypatch.setattr(EX, "_nouns", lambda pair: nouns)
    monkeypatch.setattr(EX, "_freqs", lambda pair: freqs)
    monkeypatch.setattr("review.classes.persisted_noun_classes", lambda pair: dict(store))
    written = {}
    monkeypatch.setattr("review.classes.write_noun_classes", lambda pair, a: written.update(a))
    monkeypatch.setattr(EX, "_add_affix_to_model", lambda pair, form, side, gloss: True)
    monkeypatch.setattr(EX, "_emit_pattern_delta", lambda pair, pat, side, label, ns: len(ns))
    r = EX.apply_residue_pattern("swh", "ni", side="suffix", label="LOC")
    assert r["n_candidates"] == 4                                 # mbinguni, nyumbani, duniani, amini all end -ni
    assert r["n_assigned"] == 3 and set(r["examples"]) == {"mbinguni", "nyumbani", "duniani"}
    assert r["n_skipped_by_gate"] == 1 and r["skipped_examples"] == ["amini"]   # gate caught the over-application
    assert r["residue_before"] == 5 and r["residue_after"] == 2   # 3 assigned; amini + kazi remain residue
    assert written["nyumbani"]["class"] == "LOC"

    raw = EX.apply_residue_pattern("swh", "ni", side="suffix", label="LOC", gate="none")
    assert raw["n_assigned"] == 4                                 # gate='none' reverts to raw substring (incl amini)


def test_agreement_hypotheses_ranks_concord_and_doesnt_fit(monkeypatch):
    """Per noun-class, rank the concord markers it triggers (A/B/C) with the non-dominant share as
    doesn't-fit (concord exceptions)."""
    by_pfx = {"ki": Counter({"cha": 200, "kwa": 20, "ya": 5}), "Ø": Counter({"ya": 9}),
              "n": Counter({"ya": 1})}                   # 'n' below min_support; Ø excluded
    monkeypatch.setattr("review.agreement.associative_votes", lambda pair, sample=0: (by_pfx, {}))
    monkeypatch.setattr("review.langknow.noun_class_prefixes", lambda lang: {"ki": "7"})
    r = EX.agreement_hypotheses("swh", min_support=8)
    rows = {row["noun_prefix"]: row for row in r["rows"]}
    assert "ki" in rows and "Ø" not in rows and "n" not in rows
    ki = rows["ki"]
    assert ki["class"] == "7" and ki["candidates"][0]["marker"] == "cha"   # A = dominant concord
    assert ki["candidates"][1]["marker"] == "kwa"                          # B = 2nd
    assert ki["doesnt_fit"]["n"] == 25 and "kwa" in ki["doesnt_fit"]["markers"]


def test_apply_concord_emits_decision(monkeypatch):
    monkeypatch.setattr("review.langknow.noun_class_prefixes", lambda lang: {"ki": "7"})
    monkeypatch.setattr(EX, "_set_schema_concord", lambda pair, cls, mk: True)
    monkeypatch.setattr(EX, "_emit_concord_delta", lambda pair, pfx, cls, mk: 1)
    r = EX.apply_concord("swh", "ki", "cha")
    assert r["class"] == "7" and r["marker"] == "cha" and r["schema_updated"] and r["deltas"] == 1


if __name__ == "__main__":
    import traceback

    class _MP:
        def setattr(self, obj, name, val=None):
            if val is None and isinstance(obj, str):
                import importlib
                mod, _, attr = obj.rpartition(".")
                setattr(importlib.import_module(mod), attr, name)
            else:
                setattr(obj, name, val)

    ok = 0
    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in fns:
        try:
            fn(_MP()); ok += 1; print(f"  ok  {name}")
        except Exception:
            print(f"FAIL  {name}"); traceback.print_exc()
    print(f"\n{ok}/{len(fns)} passed")
    raise SystemExit(0 if ok == len(fns) else 1)
