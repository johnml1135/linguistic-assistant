"""Offline test for the opus-as-reviewer runner: a 'promote' is APPLIED only if the candidate is also
mechanically buildable (the round-trip backstop); a 'promote' on a non-buildable candidate is recorded but
blocked by the gate; reject/defer are never applied. Disk writes (gold/deltas) are mocked."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import opus_review as OR          # noqa: E402
from review.promote import RuleCandidate      # noqa: E402


def _fake_candidates():
    return [
        RuleCandidate(id="good_buildable", pair="xx", kind="glide-collapse", description="u->w/__V",
                      members=["mu", "mw"], score=0.9, buildable=True),
        RuleCandidate(id="clean_no_emitter", pair="xx", kind="assimilation", description="meN place",
                      members=["mem", "men"], score=0.8, buildable=False),
        RuleCandidate(id="spurious", pair="xx", kind="allomorph-collapse", description="p~pe",
                      members=["p", "pe"], score=0.7, buildable=False),
    ]


def test_apply_decisions_gate_backstops_promote(monkeypatch):
    monkeypatch.setattr(OR, "build_dossiers", lambda pair: _fake_candidates())
    monkeypatch.setattr(OR, "_persist_collapse_rules", lambda pair, cs: None)
    monkeypatch.setattr(OR, "_promote_in_gold", lambda pair, ids: len(ids))
    monkeypatch.setattr(OR, "_emit_delta_ops", lambda pair, promoted: len(promoted))
    decisions = {
        "good_buildable": {"decision": "promote", "rationale": "round-trips + complementary"},
        "clean_no_emitter": {"decision": "promote", "rationale": "clean evidence but no emitter"},
        "spurious": {"decision": "reject", "rationale": "unrelated lexemes sharing an initial letter"},
    }
    r = OR.apply_decisions("xx", decisions)
    assert r["promoted_applied"] == ["good_buildable"]                 # buildable promote → applied
    assert r["promote_blocked_by_gate"] == ["clean_no_emitter"]        # promote but not buildable → blocked
    assert r["activated_in_gold"] == 1 and r["delta_ops"] == 1
    by_id = {row["id"]: row for row in r["rows"]}
    assert by_id["good_buildable"]["applied"] is True
    assert by_id["clean_no_emitter"]["applied"] is False               # approved, not applied
    assert by_id["spurious"]["decision"] == "reject" and by_id["spurious"]["applied"] is False


def test_glide_buildable_from_conditioned_grader(monkeypatch):
    """Enriched report: a glide-collapse that the BLANKET verify marks non-buildable becomes applied when the
    DATA-DRIVEN CONDITIONED round-trip is productive; a degenerate one stays blocked."""
    cands = [
        RuleCandidate(id="vi_vy", pair="xx", kind="glide-collapse", description="i->y", members=["vi", "vy"],
                      score=0.6, buildable=False, rule={}),
        RuleCandidate(id="mi_my", pair="xx", kind="glide-collapse", description="i->y", members=["mi", "my"],
                      score=0.6, buildable=False, rule={}),
    ]
    monkeypatch.setattr(OR, "build_dossiers", lambda pair: cands)
    monkeypatch.setattr(OR, "_persist_collapse_rules", lambda pair, cs: None)
    monkeypatch.setattr(OR, "_promote_in_gold", lambda pair, ids: len(ids))
    monkeypatch.setattr(OR, "_emit_delta_ops", lambda pair, promoted: len(promoted))
    # vi_vy: conditioned rule productive; mi_my: degenerate (not productive)
    monkeypatch.setattr(OR, "_enrich_glide", lambda pair, c: {
        "conditioned_round_trip": {"productive": c.id == "vi_vy", "rule": "i->y/__V[-iu]"}})
    r = OR.apply_decisions("xx", {"vi_vy": {"decision": "promote", "rationale": "conditioned productive"},
                                  "mi_my": {"decision": "promote", "rationale": "looks glide-y"}})
    assert r["promoted_applied"] == ["vi_vy"]                       # conditioned-productive → applied
    assert r["promote_blocked_by_gate"] == ["mi_my"]               # degenerate → blocked by the gate


def test_member_affixes_split_by_dash_and_kind():
    glide = RuleCandidate(id="g", pair="x", kind="glide-collapse", description="", members=["vi", "vy"])
    assert OR._member_affixes(glide) == ({"vi", "vy"}, set())          # bare + glide kind → prefixes
    harm = RuleCandidate(id="h", pair="x", kind="harmony", description="", members=["-le", "-li"])
    assert OR._member_affixes(harm) == (set(), {"le", "li"})            # leading dash → suffixes
    assim = RuleCandidate(id="a", pair="x", kind="assimilation", description="", members=["mem-", "men-"])
    assert OR._member_affixes(assim) == ({"mem", "men"}, set())         # trailing dash → prefixes


def test_unreviewed_candidate_defaults_to_defer(monkeypatch):
    monkeypatch.setattr(OR, "build_dossiers", lambda pair: _fake_candidates())
    monkeypatch.setattr(OR, "_persist_collapse_rules", lambda pair, cs: None)
    monkeypatch.setattr(OR, "_promote_in_gold", lambda pair, ids: 0)
    monkeypatch.setattr(OR, "_emit_delta_ops", lambda pair, promoted: 0)
    r = OR.apply_decisions("xx", {})                                   # no decisions provided
    assert r["promoted_applied"] == []
    assert all(row["decision"] == "defer" for row in r["rows"])        # nothing applied without a decision


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
