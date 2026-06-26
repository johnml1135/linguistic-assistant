"""Tests for the paradigm-report pipeline: schema round-trip, packet audit invariant, score separability,
and the swh noun-class slice as a regression guard."""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review.paradigm import packet as PK            # noqa: E402
from review.paradigm import profiles as PF          # noqa: E402
from review.paradigm import report as RP            # noqa: E402
from review.paradigm import score as SC             # noqa: E402
from review.paradigm.schema import Cell, ParadigmReport, golden_path  # noqa: E402


def test_schema_round_trip():
    r = ParadigmReport(language="xx", paradigm_type="case", detected=True, confidence=0.5,
                       cells=[Cell(label="acc", markers=["-i"], function="object", support=10)])
    r2 = ParadigmReport.from_dict(r.to_dict())
    assert r2.language == "xx" and r2.cells[0].markers == ["-i"]


def test_audit_catches_answer_leak():
    clean = {"language": "swh", "provenance": "x", "hypotheses": {"hypotheses": []}}
    assert PK.audit(clean) == []
    leaked = {"language": "swh", "provenance": "x", "answer_key": {"cells": ["truth"]}}
    assert any("answer_key" in v for v in PK.audit(leaked))
    assert any("provenance" in v for v in PK.audit({"language": "swh"}))


def test_swh_packet_clean_and_real():
    pkt = PK.assemble("swh", "noun-class")
    assert PK.audit(pkt) == []
    assert pkt["hc"]["n_class_groups"] >= 4
    assert pkt["thot"]["n_classes_with_concord"] >= 4


def test_score_is_separable():
    """A report that drops cells the packet HAS must lose faithfulness but keep completeness."""
    pkt = PK.assemble("swh", "noun-class")
    golden = ParadigmReport.load(golden_path("swh", "noun-class"))
    full = RP.generate(pkt, endpoint="heuristic")
    s_full = SC.score(full, golden, pkt)
    # degrade: report only the first cell
    partial = ParadigmReport(language="swh", paradigm_type="noun-class", detected=True,
                             cells=full.cells[:1])
    s_part = SC.score(partial, golden, pkt)
    assert s_part["evidence_completeness"] == s_full["evidence_completeness"]  # packet unchanged
    assert s_part["faithfulness"] < s_full["faithfulness"]                     # generator worse


def test_score_penalises_hallucination():
    pkt = PK.assemble("swh", "noun-class")
    golden = ParadigmReport.load(golden_path("swh", "noun-class"))
    rep = RP.generate(pkt, endpoint="heuristic")
    rep.cells.append(Cell(label="zz fake class", markers=["zzzq"], function="invented"))
    s = SC.score(rep, golden, pkt)
    assert s["breakdown"]["hallucination_rate"] > 0
    assert "zz fake class" in s["breakdown"]["hallucinated_cells"]


def test_profiles_emit_and_load():
    for lang in ("swh", "ind", "tgl", "spa", "tur", "vie", "hin", "rus"):
        prof = PF.load(lang)
        assert prof["language"] == lang and prof["name"]
        assert prof["paradigms"][0]["layer"] == "switches"   # layer 0 always first
        assert prof["layers"] == list(PF.LAYERS)


def test_gate_engine_atoms():
    sw = {"case": "absent", "affix_polarity": "both", "synthesis": "agglutinative"}
    assert PF.gate_ok("switch:case == absent", sw, {})
    assert not PF.gate_ok("switch:case != absent", sw, {})
    assert PF.gate_ok("switch:affix_polarity ~ suffix", sw, {})       # 'both' implies suffixing is present
    assert PF.gate_ok("switch:synthesis == agglutinative and switch:case == absent", sw, {})
    assert not PF.gate_ok("switch:synthesis == fusional and switch:case == absent", sw, {})
    assert PF.gate_ok("paradigm:x.y in {learned,confirmed}", sw, {"x.y": "learned"})
    assert not PF.gate_ok("paradigm:x.y in {learned,confirmed}", sw, {"x.y": "locked"})


def test_progressive_unlock_concord_after_class():
    sw = {"gender_or_noun_class": "noun-class", "tam_locus": "verb-prefix"}
    st = {p["id"]: "locked" for p in PF.load("swh")["paradigms"]}
    before = {p["id"] for p in PF.next_unlocked("swh", sw, st)}
    assert "swh.noun-class" in before and "swh.concord" not in before     # concord still locked
    st["swh.noun-class"] = "learned"
    after = {p["id"] for p in PF.next_unlocked("swh", sw, st)}
    assert "swh.concord" in after                                          # now it falls out


def test_tur_case_gated_on_detector():
    """The biggest-gap dependency, encoded: tur.case stays LOCKED while detect_case reports 'absent'; it
    only unlocks once the (fixed) detector reports a non-absent case switch."""
    st = {p["id"]: "locked" for p in PF.load("tur")["paradigms"]}
    locked = {p["id"] for p in PF.next_unlocked("tur", {"affix_polarity": "both", "case": "absent"}, st)}
    assert "tur.case" not in locked
    unlocked = {p["id"] for p in PF.next_unlocked("tur", {"affix_polarity": "both", "case": "present"}, st)}
    assert "tur.case" in unlocked


def test_llm_path_survives_messy_json():
    """The actual LLM path (json_schema -> complete -> json.loads -> tolerant from_dict -> score) must
    survive real-model-shaped output: unknown top-level keys, extra cell fields, missing optional fields.
    Uses a JSON-emitting mock decoupled from the golden, so the score is honest (not hand-fit)."""
    from review.paradigm.mock_report import JsonReportMockClient
    pkt = PK.assemble("swh", "noun-class")
    rep = RP.generate(pkt, client=JsonReportMockClient())   # exercises llm_report, not the heuristic
    assert rep.detected and rep.cells
    golden = ParadigmReport.load(golden_path("swh", "noun-class"))
    s = SC.score(rep, golden, pkt)
    assert s["evidence_completeness"] == 1.0          # packet has the evidence
    assert 0.0 < s["faithfulness"] < 1.0              # untuned generator -> genuinely partial, not ceiling
    assert s["breakdown"]["hallucination_rate"] == 0.0


def test_emit_preserves_runtime_state():
    PF.emit("swh", reset=True)
    PF.record_result("swh", "swh.noun-class", status="learned", metric={"overall": 0.9})
    PF.emit("swh")                                     # default emit must NOT wipe learned state
    assert PF.get_paradigm("swh", "swh.noun-class")["status"] == "learned"
    PF.emit("swh", reset=True)                         # reset DOES restore seed
    assert PF.get_paradigm("swh", "swh.noun-class")["status"] == "locked"


def test_agreement_packet_clean():
    pkt = PK.assemble("swh", "agreement")
    assert PK.audit(pkt) == []
    assert pkt["cells"] and pkt["thot"]["n_clean"] >= 2
    golden = ParadigmReport.load(golden_path("swh", "agreement"))
    s = SC.score(RP.generate(pkt, endpoint="heuristic"), golden, pkt)
    assert s["evidence_completeness"] >= 0.8          # concord evidence is strong for swh


def test_case_detector_shape_and_verdict():
    """The new suffixal case detector: returns role-covarying suffix families and a 'present' verdict for
    tur (small sample for speed)."""
    from review.paradigm.case_detect import case_hypotheses, detect_case_real
    h = case_hypotheses("tur", sample=120, min_stems=3)
    assert "rows" in h and h["rows"]
    r = h["rows"][0]
    assert {"markers", "dominant_role", "candidates", "n_stems"} <= set(r)
    value, conf, ev, _ = detect_case_real("tur", sample=120)
    assert value in ("present", "absent") and isinstance(conf, float)


def test_case_packet_partial_completeness_is_diagnostic():
    """tur/case: the detector recovers only SOME of the 6 golden cases from data (completeness < 1.0),
    while the generator faithfully reports what's in the packet — the separable metric pointing at the
    DETECTOR as the bottleneck. Guards that the gap stays visible (regression = it silently goes to 1.0)."""
    pkt = PK.assemble("tur", "case")
    assert PK.audit(pkt) == []
    golden = ParadigmReport.load(golden_path("tur", "case"))
    s = SC.score(RP.generate(pkt, endpoint="heuristic"), golden, pkt)
    assert s["evidence_completeness"] < 1.0           # detector under-recovers (the real gap)
    assert s["evidence_completeness"] >= 0.3          # but recovers a meaningful chunk (nom/dat/loc)
    assert s["faithfulness"] >= 0.8                   # generator is not the bottleneck here


def test_swh_slice_regression():
    """The swh success case: packet has all evidence (completeness 1.0) and the improved generator
    reproduces it faithfully. Guards against a regression in either the packet or the generator."""
    pkt = PK.assemble("swh", "noun-class")
    golden = ParadigmReport.load(golden_path("swh", "noun-class"))
    rep = RP.generate(pkt, endpoint="heuristic")
    s = SC.score(rep, golden, pkt)
    assert s["evidence_completeness"] == 1.0
    assert s["faithfulness"] >= 0.9
