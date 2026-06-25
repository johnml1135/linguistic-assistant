"""Offline test for the accumulate(cotrain=...) integration (switch b): with the switch on, each round runs
a co-training pass and saves the enriched model; off, it does not. run()/build_store()/cotrain are mocked."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from induce import accumulate as AC   # noqa: E402


def _patch_common(monkeypatch, ct_calls, save_calls):
    monkeypatch.setattr(AC, "run", lambda pair, seconds, amb_cap=5.0, resume=False: {
        "final_coverage": 0.5, "lexicon": {"roots": 10}, "affixes_kept": []})
    monkeypatch.setattr(AC, "build_store", lambda pair, round_no=0: {
        "new_signatures": 0, "summary": {"total": 0}, "route": {}})

    def fake_cotrain(pair, cycles=2, amb_cap=8.0, verbose=True):
        ct_calls.append(pair)
        return {"roots_added": 3, "model": object()}

    def fake_save(pair, model):
        save_calls.append(pair)
        return "x"

    import induce.cotrain as CT
    monkeypatch.setattr(CT, "cotrain", fake_cotrain)
    monkeypatch.setattr(CT, "save_model", fake_save)


def test_accumulate_without_cotrain_does_not_call_it(monkeypatch):
    ct, sv = [], []
    _patch_common(monkeypatch, ct, sv)
    r = AC.accumulate("swh", rounds=1, seconds=1, dry_after=1, cotrain=False)
    assert ct == [] and sv == []                       # switch off -> no co-training pass
    assert r["history"][0]["cotrain_added"] == 0


def test_accumulate_with_cotrain_runs_and_saves(monkeypatch):
    ct, sv = [], []
    _patch_common(monkeypatch, ct, sv)
    r = AC.accumulate("swh", rounds=1, seconds=1, dry_after=1, cotrain=True)
    assert ct == ["swh"] and sv == ["swh"]             # switch on -> co-train + save enriched model
    assert r["history"][0]["cotrain_added"] == 3


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
