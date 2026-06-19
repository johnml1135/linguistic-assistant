"""Offline smoke tests for the delta store + confidence routing."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from proposal.change_set import op_signature  # noqa: E402
from proposal.contract import ChangeSet  # noqa: E402

from deltas.emit import _freq_conf  # noqa: E402
from deltas.store import DeltaStore  # noqa: E402


def _op(conf, form="casa"):
    return {"op": "lexical.entry.create", "lexeme_form": {"spa": form}, "morph_type": "stem",
            "entry": f"entry:spa:{form}", "confidence": conf, "provenance": {"round": 1}}


def test_add_is_idempotent_and_reinforces():
    with TemporaryDirectory() as td:
        s = DeltaStore(path=Path(td) / "x.jsonl")
        assert s.add([_op(0.6)]) == 1
        assert s.add([_op(0.8)]) == 0          # same signature → merge, not a new entry
        rec = next(iter(s.by_sig.values()))
        assert rec["rounds_seen"] == 2 and rec["confidence"] == 0.8  # bumped + max confidence


def test_routing_thresholds():
    with TemporaryDirectory() as td:
        s = DeltaStore(path=Path(td) / "x.jsonl")
        s.add([_op(0.9, "a"), _op(0.6, "b"), _op(0.2, "c")])
        r = s.route(accept_at=0.85, review_at=0.5)
        assert (r.accepted, r.review, r.deferred) == (1, 1, 1)
        assert {rec["lexeme_form"]["spa"]: rec["status"] for rec in s.by_sig.values()} == \
            {"a": "accepted", "b": "review", "c": "deferred"}


def test_human_decision_locks_against_reroute():
    with TemporaryDirectory() as td:
        s = DeltaStore(path=Path(td) / "x.jsonl")
        s.add([_op(0.2, "z")])
        sig = op_signature(_op(0.2, "z"))
        assert s.decide(sig, "accept", by="human")
        r = s.route()  # would otherwise defer (0.2) — but it's locked
        assert s.by_sig[sig]["status"] == "accepted" and r.locked == 1
        # a later re-add must not overwrite the locked confidence/status
        s.add([_op(0.25, "z")])
        assert s.by_sig[sig]["status"] == "accepted" and s.by_sig[sig]["confidence"] == 0.2


def test_accepted_change_set_validates():
    with TemporaryDirectory() as td:
        s = DeltaStore(path=Path(td) / "x.jsonl")
        s.add([_op(0.9, "a"), _op(0.2, "b")])
        s.route()
        cs = s.accepted_change_set()
        assert isinstance(cs, ChangeSet) and len(cs.ops) == 1  # only the accepted one


def test_persistence_round_trips():
    with TemporaryDirectory() as td:
        p = Path(td) / "x.jsonl"
        s = DeltaStore(path=p)
        s.add([_op(0.9, "a"), _op(0.6, "b")]); s.route(); s.save()
        s2 = DeltaStore.load(p)
        assert len(s2.by_sig) == 2
        assert s2.add([_op(0.9, "a")]) == 0  # reload then re-add merges, no dup


def test_freq_conf_monotonic_and_bounded():
    assert _freq_conf(1) < _freq_conf(100) < _freq_conf(100000) <= 0.9


def test_to_minilcm_groups_and_backfills_lexemeform():
    from deltas.apply import to_minilcm
    cs = ChangeSet(ops=[
        {"op": "lexical.entry.create", "entry": "entry:spa:casa", "lexeme_form": {"spa": "casa"}, "morph_type": "stem"},
        {"op": "lexical.sense.create", "entry": "entry:spa:casa", "gloss": {"en": "house"}},
        {"op": "lexical.entry.set_pos", "entry": "entry:spa:casa", "pos": "noun"},
        {"op": "lexical.sense.create", "entry": "entry:spa:dios", "gloss": {"en": "god"}},  # sense-only
    ])
    ents = {e["id"]: e for e in to_minilcm(cs)}
    assert ents["entry:spa:casa"]["lexemeForm"] == {"spa": "casa"}
    assert ents["entry:spa:casa"]["partOfSpeech"] == "noun"
    assert ents["entry:spa:casa"]["senses"] == [{"gloss": {"en": "house"}}]
    assert ents["entry:spa:dios"]["lexemeForm"] == {"spa": "dios"}  # backfilled from the entry id


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
