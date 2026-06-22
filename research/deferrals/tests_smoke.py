"""Offline smoke tests for the deferral-package spine (Phase A).

Everything here runs with no LLM. The HC counterfactual-flip test is skipped when the `hc` CLI is
absent; all other tests (schema, store, taxonomy, builder, options, impact, dependencies, edit→delta
mapping, render) are fully offline and never touch the real gold or the real delta store.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from golden.reference.hc_coverage import hc_available  # noqa: E402

from deferrals import build, edits as E, store as S, taxonomy  # noqa: E402
from deferrals.counterfactual import attach_counterfactuals, load_base, related_verses  # noqa: E402
from deferrals.render import render  # noqa: E402
from deferrals.schema import (  # noqa: E402
    Counterfactual, DeferralTicket, GrammarEdit, Hypothesis, PresentationOption, Resolution,
    read_jsonl, write_jsonl,
)

PAIR = "spa"
GOLD = build.load_gold(PAIR)

# a representative lexical defer record (shape produced by propose.py)
LEX_REC = {"word": "abriere", "gloss": "open", "pos": "Verb", "conf": "medium",
           "aligner_top1": "open", "current_gold": None, "decision": "defer", "source": "test"}
# an affix-function defer record (shape produced by propose_morph)
AFF_REC = {"affix": "ndo", "kind": "suffix", "function": "gerund", "feature": {"Aspect": "Prog"},
           "conf": "medium", "source": "test"}


def _sample_ticket() -> DeferralTicket:
    h = Hypothesis(id="h1", mechanism="add_lexentry", description="new root",
                   edits=[GrammarEdit("add_lexentry", {"form": "abriere", "gloss": "open", "pos": "Verb"})],
                   counterfactuals=[Counterfactual(ref="MAT 1:1", text="abriere de", focus="abriere",
                                                   now={"abriere": []}, if_hyp={"abriere": [["open"]]},
                                                   focus_parsed_now=False, focus_parsed_if=True)])
    return DeferralTicket(
        id="spa-lexeme_gloss-abriere", pair=PAIR, type="lexeme_gloss", domain="lexical",
        target={"form": "abriere", "gloss": "open"}, confidence=0.5,
        impact={"freq": 3, "wordforms": 5, "score": 40, "priority": "medium"},
        hypotheses=[h], presentation_options=[PresentationOption("o1", "elicit_meaning", "open", "What does X mean?")],
        resolution=Resolution())


def test_schema_validates_and_roundtrips(tmp_path):
    t = _sample_ticket()
    t.validate()
    p = tmp_path / "tickets.jsonl"
    write_jsonl([t], p)
    back = read_jsonl(p)
    assert len(back) == 1
    b = back[0]
    assert b.id == t.id and b.type == "lexeme_gloss"
    assert isinstance(b.hypotheses[0], Hypothesis)
    assert isinstance(b.hypotheses[0].edits[0], GrammarEdit)
    assert isinstance(b.hypotheses[0].counterfactuals[0], Counterfactual)
    assert b.to_dict() == t.to_dict()


def test_schema_rejects_bad_enums():
    t = _sample_ticket()
    t.type = "bogus"
    with pytest.raises(AssertionError):
        t.validate()


def test_store_roundtrip_and_lifecycle(tmp_path):
    st = S.TicketStore(PAIR, path=tmp_path / "tickets.jsonl")
    st.upsert([_sample_ticket()])
    st.save()
    st2 = S.TicketStore(PAIR, path=tmp_path / "tickets.jsonl")
    assert len(st2.tickets) == 1
    tid = st2.tickets[0].id
    assert st2.start_review(tid)
    assert st2.get(tid).status == "in_review"
    assert st2.get(tid).history[-1]["to"] == "in_review"


def test_taxonomy_lexical_hypotheses():
    ttype, domain, hyps = taxonomy.enumerate_hypotheses(LEX_REC, GOLD)
    assert ttype in ("lexeme_gloss", "homograph") and domain == "lexical"
    assert hyps and any(h.mechanism == "add_lexentry" for h in hyps)
    for h in hyps:
        h.validate()


def test_taxonomy_profile_filter_prunes():
    # if only add_lexentry is allowed, no allomorph/resegment hypotheses survive
    _, _, hyps = taxonomy.enumerate_hypotheses(LEX_REC, GOLD, allowed={"add_lexentry"})
    assert hyps and all(all(e.kind == "add_lexentry" for e in h.edits) for h in hyps)


def test_taxonomy_affix_hypotheses():
    ttype, domain, hyps = taxonomy.enumerate_hypotheses(AFF_REC, GOLD)
    assert ttype == "affix_function" and domain == "morphology"
    assert any(h.mechanism == "add_affix" for h in hyps)


def test_build_ticket_offline_is_complete():
    t = build.build_ticket(PAIR, LEX_REC, gold=GOLD, with_counterfactuals=False)
    t.validate()
    assert t.hypotheses, "expected ≥1 hypothesis"
    assert len(t.presentation_options) >= 5, f"expected ≥5 options, got {len(t.presentation_options)}"
    assert t.impact["priority"] in ("high", "medium", "low")
    assert t.context_md and t.confidence >= 0.0
    # options are tagged with the hypotheses they discriminate
    assert any(o.discriminates for o in t.presentation_options)


def test_build_all_links_dependencies():
    recs = [LEX_REC, {**LEX_REC, "word": "abriereis"}]   # share the 'abri' stem
    tickets = build.build_all(PAIR, recs, with_counterfactuals=False)
    assert len(tickets) == 2
    assert tickets[0].dependencies and tickets[1].dependencies
    assert tickets[1].id in tickets[0].dependencies


def test_impact_orders_by_frequency():
    common = build.compute_impact(PAIR, "que", GOLD)        # a very frequent function word stem
    rare = build.compute_impact(PAIR, "zzqxv", GOLD)
    assert common["score"] >= rare["score"]


def test_edits_to_ops_are_valid_change_set():
    from proposal.change_set import validate_change_set
    import json as _json
    t = _sample_ticket()
    ops = S.edits_to_ops(t, t.hypotheses[0])
    assert ops, "expected ops from add_lexentry"
    cs = validate_change_set(_json.dumps({"ops": ops}))
    from proposal.contract import ChangeSet
    assert isinstance(cs, ChangeSet), cs


def test_resolve_writes_deltas(tmp_path):
    st = S.TicketStore(PAIR, path=tmp_path / "tickets.jsonl", delta_dir=tmp_path / "deltas")
    st.upsert([_sample_ticket()])
    tid = st.tickets[0].id
    res = Resolution(action="accept_option", hypothesis_id="h1", by="tester")
    out = st.resolve(tid, res)
    assert out["ok"] and out["status"] == "resolved" and out["ops"] >= 1
    assert (tmp_path / "deltas" / f"{PAIR}.deltas.jsonl").exists()
    assert st.get(tid).resolution.action == "accept_option"


def test_resolve_reject_is_wont_fix_no_deltas(tmp_path):
    st = S.TicketStore(PAIR, path=tmp_path / "tickets.jsonl", delta_dir=tmp_path / "deltas")
    st.upsert([_sample_ticket()])
    tid = st.tickets[0].id
    out = st.resolve(tid, Resolution(action="reject_with_reason", reason="not a word", by="tester"))
    assert out["ok"] and out["status"] == "wont_fix" and out["ops"] == 0
    assert not (tmp_path / "deltas" / f"{PAIR}.deltas.jsonl").exists()


def test_render_is_derived_from_json():
    md = render(_sample_ticket())
    assert "# Resolution ticket" in md and "abriere" in md
    assert "now" in md and "if-true" in md            # counterfactual diff is shown
    assert "ask the speaker" in md.lower()


def test_related_verses_deterministic():
    a = related_verses(PAIR, "amor")
    b = related_verses(PAIR, "amor")
    assert a == b and len(a) >= 1


def test_profile_seed_and_roundtrip(tmp_path, monkeypatch):
    from deferrals import profile as P
    prof = P._seed("swh")
    assert prof.morph_type == "agglutinative"
    # Swahili: noun-class present, gender locked-off (the key constraint)
    assert prof.feature_present("noun_class") and not prof.feature_present("gender")
    assert prof.feature_space["gender"].locked
    # round-trip through dict
    back = P.LanguageProfile.from_dict(prof.to_dict())
    assert back.to_dict() == prof.to_dict()
    # features carry pre-written explanations
    ex = prof.feature_space["noun_class"].explanation()
    assert ex and "plain" in ex and ex["sources"]


def test_profile_constrains_affix_kinds():
    from deferrals import profile as P
    spa = P._seed("spa")
    # Spanish: infix + reduplication locked off; prefix/suffix allowed
    assert "suffix" in spa.allowed_affix_kinds() and "prefix" in spa.allowed_affix_kinds()
    assert "infix" not in spa.allowed_affix_kinds()
    assert "reduplication" not in spa.allowed_affix_kinds()
    tgl = P._seed("tgl")
    assert "infix" in tgl.allowed_affix_kinds()       # Tagalog allows infixation


def test_taxonomy_pruned_by_profile_infix():
    from deferrals import profile as P
    spa = P._seed("spa")
    rec = {"affix": "um", "kind": "infix", "function": "actor focus", "conf": "medium"}
    _, _, hyps = taxonomy.enumerate_hypotheses(rec, GOLD, allowed_affix_kinds=spa.allowed_affix_kinds())
    assert hyps == [], "an infix hypothesis must be pruned for non-infixing Spanish"


def test_per_language_bar_on_ticket():
    from deferrals import profile as P
    t = build.build_ticket(PAIR, LEX_REC, gold=GOLD, profile=P._seed(PAIR), with_counterfactuals=False)
    assert t.tags["auto_accept_bar"] == 0.995 and t.tags["morph_type"] == "fusional"


def test_select_rank_targets_prefers_resolvable_and_frequent():
    from deferrals import select
    # 'amar' shares a stem with many frequent forms; a random isolated string does not
    rows = select.rank_targets(PAIR, ["amare", "zzqxv", "amados"], gold=GOLD)
    assert rows[0]["word"] in ("amare", "amados")
    assert rows[-1]["word"] == "zzqxv"
    assert all("resolvability" in r and "impact" in r for r in rows)


def test_select_cluster_forms_groups_one_lexeme():
    from deferrals import select
    cl = select.cluster_forms(PAIR, ["amare", "amaras", "amado", "comer"],
                              en_of={"amare": "love", "amaras": "love", "amado": "love", "comer": "eat"})
    forms = {f for c in cl for f in c["forms"]}
    assert "amare" in forms and "amaras" in forms and "comer" not in forms


def test_auto_accept_gate_two_signals_and_bar():
    from deferrals import auto_accept as AA
    recs = [
        {"word": "amor", "gloss": "love", "aligner_top1": "love", "conf": "high"},       # concur → accept
        {"word": "x", "gloss": "thing", "aligner_top1": "stuff", "conf": "high"},         # disagree → defer
        {"word": "y", "gloss": "maybe", "aligner_top1": "maybe", "conf": "low"},          # low → defer
        {"affix": "s", "gloss": "PL", "aligner_top1": "PL", "conf": "high"},              # morphology → defer
    ]
    out = AA.gate(PAIR, recs)
    assert out["bar"] == 0.995
    assert out["n_accepted"] == 1 and out["accepted"][0]["word"] == "amor"
    assert out["accepted"][0]["source"] == "ai-auto" and out["accepted"][0]["signals"]
    assert out["n_deferred"] == 3                       # incl. the affix (never auto-accept morphology)


def test_auto_accept_precision_and_bar_check():
    from deferrals import auto_accept as AA
    acc = [{"word": "amor", "gloss": "love"}, {"word": "casa", "gloss": "house"}]
    truth = {"amor": "love", "casa": "home; house"}
    m = AA.measure_precision(acc, truth)
    assert m["precision"] == 1.0 and AA.meets_bar(m["precision"], 0.995)
    assert not AA.meets_bar(0.99, 0.995)


def test_corpus_slice_deterministic_and_focus_first():
    from deferrals.assess import corpus_slice
    a = corpus_slice(PAIR, "amor", n=30)
    b = corpus_slice(PAIR, "amor", n=30)
    assert a == b and a[0] == "amor" and len(a) <= 30


@pytest.mark.skipif(not hc_available(), reason="hc CLI not installed")
def test_assess_true_fix_beats_decoy_on_ablation():
    """Stage-4 ground-truth check: re-adding the ablated lexeme is acceptable; the over-broad decoy is not
    (and is no better on ΔMDL). This is the regression-aware assessment working against a known answer."""
    from deferrals import assess as A, validation as V
    base, pf = load_base(PAIR)
    scen = V.ablate(PAIR, "lex", rank=0, base=base, pf=pf, n_slice=40)
    if not scen["broken"]:                       # ablated lexeme broke nothing parseable → skip
        pytest.skip("ablation broke no parseable forms in the slice")
    crippled, words, focus = scen["crippled"], scen["words"], scen["focus"]
    truth, decoy = V.true_hypothesis(scen), V.decoy_hypothesis(scen)
    A.assess_hypothesis(PAIR, truth, focus, base=crippled, pf=pf, words=words)
    A.assess_hypothesis(PAIR, decoy, focus, base=crippled, pf=pf, words=words)
    assert truth.verdict["acceptable"], truth.verdict
    assert truth.metrics["net_delta"] >= 1, truth.metrics
    # the decoy must not be ranked better than the truth: either not acceptable, or worse/equal ΔMDL
    assert (not decoy.verdict["acceptable"]) or truth.metrics["delta_mdl"] <= decoy.metrics["delta_mdl"]


@pytest.mark.skipif(not hc_available(), reason="hc CLI not installed")
def test_assess_ticket_ranks_and_sets_metrics():
    from deferrals import assess as A
    rec = {"word": "amare", "gloss": "love", "pos": "Verb", "conf": "medium", "aligner_top1": "love",
           "decision": "defer"}
    t = build.build_ticket(PAIR, rec, gold=GOLD, with_counterfactuals=False)
    out = A.assess_ticket(t, n_slice=40)
    assert out["ranking"] and all(h.metrics for h in t.hypotheses)
    assert all("delta_mdl" in h.metrics and "net_delta" in h.metrics for h in t.hypotheses)


def test_infix_hypothesis_gated_by_profile():
    from deferrals import profile as P
    # Tagalog allows infixation: 'sumulat' → stem 'sulat' + infix -um-
    tgl = P._seed("tgl")
    rec = {"word": "sumulat", "gloss": "write", "aligner_top1": "write"}
    _, _, hyps = taxonomy.enumerate_hypotheses(rec, {"lemmas": [], "senses": {}, "affixes": []},
                                               allowed_affix_kinds=tgl.allowed_affix_kinds())
    infix_hyps = [h for h in hyps if any(
        e.kind == "resegment" and any(s.get("params", {}).get("kind") == "infix"
                                      for s in e.params.get("edits", [])) for e in h.edits)]
    assert infix_hyps, "expected an infix re-segmentation hypothesis for Tagalog"
    # Spanish locks infixation off → no infix hypothesis even for an infix-looking word
    spa = P._seed("spa")
    _, _, hyps2 = taxonomy.enumerate_hypotheses(rec, {"lemmas": [], "senses": {}, "affixes": []},
                                                allowed_affix_kinds=spa.allowed_affix_kinds())
    assert not any(any(e.kind == "resegment" and any(s.get("params", {}).get("kind") == "infix"
                       for s in e.params.get("edits", [])) for e in h.edits) for h in hyps2)


def test_archiphoneme_collapse_detected_for_allomorph_family():
    # an Indonesian-style meN- family: same function, differ by a trailing segment → collapse hypothesis
    gold = {"affixes": [{"affix": "mem", "features": "AV"}, {"affix": "meng", "features": "AV"},
                        {"affix": "men", "features": "AV"}], "lemmas": [], "senses": {}}
    rec = {"affix": "meny", "kind": "prefix", "function": "AV"}
    _, _, hyps = taxonomy.enumerate_hypotheses(rec, gold)
    collapse = [h for h in hyps if h.mechanism == "add_phon_rule"]
    assert collapse, "expected an archiphoneme-collapse hypothesis for the allomorph family"
    members = collapse[0].edits[0].params["members"]
    assert "mem" in members and "meng" in members


def test_escalation_router_high_impact_and_clusters():
    from deferrals import pipeline
    hi = _sample_ticket()
    hi.impact["priority"] = "high"
    lo = _sample_ticket()
    lo.impact["priority"] = "low"
    lo.dependencies = []
    assert pipeline.should_escalate(hi)
    assert not pipeline.should_escalate(lo)
    clustered = _sample_ticket()
    clustered.impact["priority"] = "low"
    clustered.dependencies = ["a", "b", "c"]
    assert pipeline.should_escalate(clustered)


def test_state_aware_weighting_changes_order_weight():
    from deferrals import select
    # state only changes the resolvability weighting; both runs must be deterministic + well-formed
    cold = select.rank_targets(PAIR, ["amare", "amados", "zzqxv"], gold=GOLD, state="cold")
    mature = select.rank_targets(PAIR, ["amare", "amados", "zzqxv"], gold=GOLD, state="mature")
    assert {r["word"] for r in cold} == {r["word"] for r in mature}
    assert cold[-1]["word"] == "zzqxv"                    # the unresolvable isolate is last either way


def test_derivation_inflection_tag():
    assert taxonomy.affix_function_kind("causative") == "derivational"
    assert taxonomy.affix_function_kind("NMLZ") == "derivational"
    assert taxonomy.affix_function_kind("Tense=Past") == "inflectional"


def test_followon_stubs_flagged_when_profile_allows():
    from deferrals import profile as P
    tgl = P._seed("tgl")                                  # allows reduplication + has concord
    stubs = taxonomy.followon_stubs("balikbalik", tgl)    # a doubled form
    mechs = {s.mechanism for s in stubs}
    assert "reduplication" in mechs
    assert all(s.source == "follow-on" and s.unverified and not s.edits for s in stubs)
    spa = P._seed("spa")                                  # reduplication locked off
    assert "reduplication" not in {s.mechanism for s in taxonomy.followon_stubs("balikbalik", spa)}


def test_build_ticket_has_edge_cases_and_stubs():
    from deferrals import profile as P
    t = build.build_ticket(PAIR, {"word": "amare", "gloss": "love", "aligner_top1": "love"},
                           gold=GOLD, profile=P._seed(PAIR), with_counterfactuals=False)
    assert "edge_cases" in t.tags                          # edge-case selector ran (may be empty offline)


def test_defer_scenario_marks_unresolvable():
    from deferrals import validation as V
    s = V.defer_scenario(PAIR, "zzqortxx")                 # isolated non-word
    assert s["expected"] == "defer" and not s["resolvable"]


def test_conflict_report_runs():
    from deferrals import profile as P
    rep = P.conflict_report(PAIR)                           # spa: should be few/no conflicts
    assert isinstance(rep, list)
    for r in rep:
        assert "feature" in r and "profile_says" in r and "corpus_evidence" in r


def test_llm_helpers_graceful_without_endpoint():
    """All Phase B/C LLM steps must degrade safely (defer / no-op) when no endpoint is reachable."""
    from deferrals import llm
    bad = "definitely_not_a_real_endpoint_xyz"
    d = llm.resolve_or_defer({"form": "x", "pair": PAIR}, endpoint=bad)
    assert d["decision"] == "defer" and d["edit"] == {}     # never guesses without a model
    t = build.build_ticket(PAIR, LEX_REC, gold=GOLD, with_counterfactuals=False)
    v = llm.llm_verdict(t, endpoint=bad)
    assert v["ok"] in (True, False)                          # no crash
    pf = llm.propose_feature(PAIR, "affix_processes", "reduplication", ["aa", "bb"], endpoint=bad)
    assert pf["ok"] is False
    fo = llm.fanout_investigate(t, endpoint=bad)
    assert fo["ok"] is False and fo["added"] == 0


def test_eval_gemma_sets_have_ground_truth():
    from deferrals import eval_gemma as EG
    res = EG._resolvable_set(PAIR, GOLD, 5)
    deferr = EG._defer_set(PAIR, 4)
    assert res and all(r["truth_gloss"] and r["form"] for r in res)
    assert deferr and all(d["pivot_gloss"] == "?" and d["near_lemma"] is None for d in deferr)


def test_webui_seed_render_and_resolve(tmp_path):
    """The throwaway review UI is a pure consumer of deferrals/ — seed, render, resolve, all offline."""
    from deferrals import webui
    st = S.TicketStore(PAIR, path=tmp_path / "tickets.jsonl", delta_dir=tmp_path / "deltas")
    assert webui.seed_demo(st) >= 1 and st.tickets
    q = webui.queue_html(st)
    assert "Issue queue" in q and st.tickets[0].id in q
    tid = st.tickets[0].id
    h = webui.ticket_html(st, tid)
    assert "Resolution ticket" in h and "Resolve" in h          # open ticket shows the resolve form
    st.resolve(tid, Resolution(action="reject_with_reason", reason="demo", by="t"))
    assert "wont_fix" in webui.ticket_html(st, tid)             # resolved ticket: status shown, no form


def test_webui_md_to_html_minimal():
    from deferrals import webui
    out = webui._md_to_html("# Title\n## Section\n- item\nplain")
    assert "<h1>Title</h1>" in out and "<h2>Section</h2>" in out and "<li>item</li>" in out


def test_backlog_dedup_and_build(tmp_path):
    from deferrals import backlog as B
    recs = [{"word": "amare", "source": "a"}, {"word": "amare", "source": "b"},
            {"affix": "ndo", "source": "c"}, {"word": "casa", "source": "d"}]
    deduped = B._dedup(recs)
    assert len(deduped) == 3 and [r.get("word") or r.get("affix") for r in deduped] == ["amare", "ndo", "casa"]
    # build a backlog from injected records only (no propose/discover) — offline
    st = S.TicketStore(PAIR, path=tmp_path / "tickets.jsonl")
    import deferrals.backlog as BB
    # monkeypatch the store target by building directly
    recs2 = [{"word": "amare", "gloss": "love", "aligner_top1": "love", "conf": "low",
              "decision": "defer", "source": "concept-discovery"}]
    tickets = build.build_all(PAIR, recs2, with_counterfactuals=False)
    st.upsert(tickets); st.save()
    assert st.tickets and st.tickets[0].tags["source"] == "concept-discovery"


def test_discover_shared_core_maximum_span():
    from deferrals import discover
    assert discover._shared_core(["mkono", "mikono", "mkononi"]) == ("kono", 3)
    assert discover._shared_core(["abc"]) == ("", 0)          # single word → no shared span
    core, cov = discover._shared_core(["amare", "amaras", "amado"])
    assert core.startswith("ama") and cov == 3


def test_discover_candidates_and_defer_record():
    from deferrals import discover
    from collections import Counter
    by_src = {"hand": ["mkono", "mkononi"], "hands": ["mikono"]}
    freqs = Counter({"mkono": 110, "mikono": 30, "mkononi": 12})
    cands = discover.candidates_for("hand", by_src, freqs)
    forms = [w for w, _ in cands]
    assert "mkono" in forms and "mikono" in forms and forms[0] == "mkono"   # freq-ranked
    rep = {"concept": "hand", "candidates": [{"form": "mkono", "count": 110, "parse": []}],
           "shared_core": "kono", "best_form": "mkono", "proposed_lexeme": "kono", "examples": []}
    rec = discover.to_defer_record(rep)
    assert rec["word"] == "kono" and rec["aligner_top1"] == "hand" and rec["decision"] == "defer"
    # the record is exactly what build_ticket consumes
    build.build_ticket(PAIR, rec, gold=GOLD, with_counterfactuals=False).validate()


def test_enrich_graceful_without_endpoint():
    """Phase B must degrade to a no-op (never crash, never drop deterministic hypotheses) with no endpoint."""
    from deferrals import enrich
    t = build.build_ticket(PAIR, LEX_REC, gold=GOLD, with_counterfactuals=False)
    n_before = len(t.hypotheses)
    out = enrich.enrich(t, endpoint="definitely_not_a_real_endpoint_xyz")
    assert out["ok"] is False and out["added"] == 0
    assert len(t.hypotheses) == n_before               # deterministic hypotheses untouched


@pytest.mark.skipif(not hc_available(), reason="hc CLI not installed")
def test_score_pipeline_stages_measured():
    from deferrals import pipeline
    s = pipeline.score_pipeline(PAIR, n_lex=1, n_affix=1, n_slice=30)
    assert s["scenarios"] >= 1
    for k in ("stage2_selection_recall", "stage3_hypothesis_recall",
              "stage4_true_accept_rate", "stage4_decoy_reject_rate"):
        assert s[k] is None or 0.0 <= s[k] <= 1.0
    assert s["stage4_true_accept_rate"] == 1.0          # the true re-add must be accepted


@pytest.mark.skipif(not hc_available(), reason="hc CLI not installed")
def test_counterfactual_flip_and_gold_untouched():
    base, pf = load_base(PAIR)
    n_lex_before = len(base.lexicon)
    # a clearly non-word that the gold cannot parse; adding it as a root must make it parse
    focus = "zzqortx"
    hyp = Hypothesis(id="h1", mechanism="add_lexentry", description="add root",
                     edits=[GrammarEdit("add_lexentry", {"form": focus, "gloss": "TESTROOT", "pos": "Noun"})])
    attach_counterfactuals(PAIR, [hyp], focus, base=base, pf=pf, n_related=1)
    assert len(base.lexicon) == n_lex_before, "gold model was mutated!"
    cf = hyp.counterfactuals[0]
    assert cf.focus_parsed_if and not cf.focus_parsed_now
