"""Offline test for the what-if comparison: given parsed sets per option, compute coverage, gained/lost vs
baseline, and the 'fit-neither' residue (words broken by EVERY option). Parsing is mocked."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import reviewer_query as RQ   # noqa: E402


def test_compare_options_gained_lost_and_fit_neither(monkeypatch):
    TEST = ["vitu", "vyombo", "mioyo", "miaka", "kitu"]   # 5 words
    # baseline parses all 5; option A breaks mioyo+miaka (the mi- over-application); option B breaks them too
    parsed = {
        "baseline": {"vitu", "vyombo", "mioyo", "miaka", "kitu"},
        "A": {"vitu", "vyombo", "kitu"},                  # lost mioyo, miaka
        "B": {"vitu", "vyombo", "kitu", "miaka"},         # lost only mioyo
    }
    monkeypatch.setattr(RQ, "_parsed", lambda pair, opt, words, pf, templated=True: (parsed[opt.name], 1.5))
    monkeypatch.setattr("induce.tdd._load_prior_model", lambda pair: type("M", (), {"charset": "abc"})())
    monkeypatch.setattr("induce.tdd.load_freqs",
                        lambda pair: __import__("collections").Counter({w: 1 for w in TEST}))
    monkeypatch.setattr("gold.phonology_gold.phon_feats", lambda pair, charset: {})

    r = RQ.compare_options("swh", [RQ.Option("A"), RQ.Option("B")], test_words=TEST)
    assert r["baseline"]["coverage"] == 1.0
    a = next(o for o in r["options"] if o["name"] == "A")
    b = next(o for o in r["options"] if o["name"] == "B")
    assert a["n_lost"] == 2 and set(a["lost_examples"]) == {"mioyo", "miaka"}
    assert b["n_lost"] == 1 and b["lost_examples"] == ["mioyo"]
    # fit-neither = parsed at baseline but broken by EVERY option → only mioyo (B keeps miaka)
    assert r["fit_neither"]["n"] == 1 and r["fit_neither"]["examples"] == ["mioyo"]


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
    for k, v in sorted(globals().items()):
        if k.startswith("test_") and callable(v):
            try:
                v(_MP()); ok += 1; print(f"  ok  {k}")
            except Exception:
                print(f"FAIL {k}"); traceback.print_exc()
    print(f"\n{ok} passed")
