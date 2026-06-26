"""Opus-as-reviewer runner — present evidence dossiers for proposed morphophonological rules, take Opus's
decisions (promote / defer / reject) made under the [[opus-as-reviewer]] firewall (decide from the dossier
+ universal method, never from recalled language knowledge), and apply the approved ones.

The tooling does the mechanical work (raise candidates, run the Hermit Crab round-trip, compute support);
this module lays that out as a per-candidate dossier and lets the reviewer take the seat the automatic
threshold in `promote.classify` otherwise fills. The round-trip stays the hard backstop: an Opus 'promote'
is APPLIED only if the rule is also mechanically buildable (it round-trips) — Opus judges the analysis,
Hermit Crab proves the forms.

CLI:
  python -m review.opus_review --pair swh                 # print dossiers for review
  python -m review.opus_review --pair swh --apply DECISIONS.json   # apply Opus's decisions
DECISIONS.json: {"<candidate id>": {"decision": "promote|defer|reject", "rationale": "...cites dossier..."}}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review.promote import (raise_candidates, verify, _persist_collapse_rules,  # noqa: E402
                            _promote_in_gold, _delta_op)


def build_dossiers(pair: str) -> list:
    """Raise + mechanically verify every rule candidate; return the verified RuleCandidates (each carries
    the detector evidence in .rule and the round-trip result the reviewer reads)."""
    return [verify(c) for c in raise_candidates(pair)]


_VOWELS = set("aeiou")


def _following_segment_profile(pair: str, prefix: str) -> dict:
    """Token counts of the segment FOLLOWING `prefix` across all corpus words — the finer environment a
    coarse vowel/consonant class destroys. (Computable from the corpus; no language knowledge.)"""
    from collections import Counter
    from align.morph_align_hc import _verses
    fol: Counter = Counter()
    for _ref, _src, tgt in _verses(pair, 0):
        for w in tgt:
            if w.startswith(prefix) and len(w) > len(prefix):
                fol[w[len(prefix)]] += 1
    return dict(fol.most_common())


def _enrich_glide(pair: str, c) -> dict:
    """For a glide-collapse candidate, add the report fields that move review F1 (advisor): the
    following-VOWEL contrast for the retained vs glide form, a DATA-DRIVEN conditioned round-trip (block the
    vowels where the retained form wins — no recall, pure distribution), and the productivity verdict from
    the mechanical grader under that conditioning."""
    from engine.hc_collapse import GLIDE_OF
    from review.promote import _glide_shape
    shape = _glide_shape(c.rule)
    if not shape:
        return {}
    ur, glide_form = shape["ur"], shape["glide_form"]
    ret_fol = {v: n for v, n in _following_segment_profile(pair, ur).items() if v in _VOWELS}
    gl_fol = {v: n for v, n in _following_segment_profile(pair, glide_form).items() if v in _VOWELS}
    # data-driven blockers: vowels where the RETAINED form is at least as frequent as the glide form
    blockers = sorted(v for v in _VOWELS if ret_fol.get(v, 0) >= gl_fol.get(v, 0) and ret_fol.get(v, 0) > 0)
    out = {"following_vowel": {"retained(" + ur + ")": ret_fol, "glide(" + glide_form + ")": gl_fol},
           "data_driven_blockers": blockers}
    try:
        from engine.hc_collapse import glide_collapse_round_trips
        from review.allomorph import member_words
        from assess.metrics import tolerance_productive
        urw, glw = member_words(pair, ur), member_words(pair, glide_form)
        rt = glide_collapse_round_trips(shape["ur"], shape["vowel"], shape["glide"], urw, glw,
                                        block_vowels=frozenset(blockers))
        n_env, exc = rt.get("n_env", 0), rt.get("n_exceptions", 0)
        # GUARD against the degenerate case (mi/my): if blockers cover every vowel the glide form occurs
        # before, the "conditioned rule" derives nothing — that is the rule's ABSENCE, not a productive rule.
        trigger_support = sum(n for v, n in gl_fol.items() if v not in blockers)
        degenerate = trigger_support < 10
        tol = tolerance_productive(n_env, exc) if n_env >= 2 else {"productive": False}
        productive = bool(tol.get("productive")) and not degenerate
        out["conditioned_round_trip"] = {
            "rule": rt.get("rule"), "n_env": n_env, "exceptions": exc, "recall": rt.get("recall_env"),
            "glide_trigger_support": trigger_support, "degenerate": degenerate,
            "productive": productive, "residual": rt.get("failures"),
            "note": "DEGENERATE: glide form has no real unblocked triggering environment — not a rule"
                    if degenerate else ""}
    except Exception as e:
        out["conditioned_round_trip"] = {"error": str(e)}
    return out


WHATIF_FLOOR = 0.20      # attach a what-if to every candidate at least this confident


def _glide_blockers(pair: str, ur: str, glide_form: str) -> list[str]:
    """Data-driven blockers: vowels where the RETAINED form is at least as frequent as the glide form."""
    ret = {v: n for v, n in _following_segment_profile(pair, ur).items() if v in _VOWELS}
    gl = {v: n for v, n in _following_segment_profile(pair, glide_form).items() if v in _VOWELS}
    return sorted(v for v in _VOWELS if ret.get(v, 0) >= gl.get(v, 0) and ret.get(v, 0) > 0)


def _member_affixes(c):
    """(prefix forms, suffix forms) the candidate's members denote: -x = suffix, x- = prefix, bare = by kind."""
    pre, suf = set(), set()
    for m in c.members:
        bare = m.strip("-")
        if not bare:
            continue
        if m.startswith("-"):
            suf.add(bare)
        elif m.endswith("-"):
            pre.add(bare)
        else:
            (pre if "prefix" in c.kind or c.kind == "glide-collapse" else suf).add(bare)
    return pre, suf


def _glide_hypotheses(pair: str, c, max_h: int = 5) -> list:
    """Generate competing MORPHEME-SCOPED conditioning hypotheses for a glide collapse, to be ranked into
    A (best guess) / B / C. Each hypothesis = one conditioned affix where the marked allomorph (e.g. vy-)
    fires before a candidate TRIGGER vowel set and the default (vi-) elsewhere. The candidate trigger sets
    are nested by how strongly each following vowel favours the glide form in the data (vy/(vy+vi) share) —
    so the hypotheses span 'glide only before the most glide-favouring vowel' … 'glide before any vowel'."""
    from review.reviewer_query import Option
    from review.promote import _glide_shape
    shape = _glide_shape(c.rule)
    if not shape:
        return []
    ur, gf = shape["ur"], shape["glide_form"]
    ret = {v: n for v, n in _following_segment_profile(pair, ur).items() if v in _VOWELS}
    gl = {v: n for v, n in _following_segment_profile(pair, gf).items() if v in _VOWELS}
    vdata = [v for v in _VOWELS if (ret.get(v, 0) + gl.get(v, 0)) > 0]
    share = {v: gl.get(v, 0) / (ret.get(v, 0) + gl.get(v, 0)) for v in vdata}
    order = sorted(vdata, key=lambda v: -share[v])        # vowels most favouring the glide first
    opts, seen = [], set()
    for k in range(1, len(order) + 1):
        trig = tuple(sorted(order[:k]))
        if trig in seen:
            continue
        seen.add(trig)
        cond = ({"gloss": f"{ur}/{gf}", "kind": "prefix",
                 "allomorphs": [{"shape": gf, "first": list(trig)}, {"shape": ur, "first": None}]},)
        opts.append(Option(f"{gf}- before {{{','.join(trig)}}} · {ur}- elsewhere",
                           prune_prefixes=frozenset({ur, gf}), conditioned_affixes=cond))
        if len(opts) >= max_h:
            break
    return opts


def _whatif_options(pair: str, c) -> list:
    """Grammar-edit options to simulate FROM a candidate. Glide-collapse gets a real live simulation (prune
    the glide-form prefix; the conditioned rule, and prune-only for contrast); other kinds get a prune-only
    option (no live emitter yet — shows what the enumerated allomorphs are covering)."""
    from review.reviewer_query import Option
    from review.promote import _glide_shape
    if c.kind == "glide-collapse":
        hyps = _glide_hypotheses(pair, c)
        if hyps:
            return hyps
    pre, suf = _member_affixes(c)
    return [Option(f"prune {sorted(pre | suf)} (no live rule — shows what it must recover)",
                   prune_prefixes=frozenset(pre), prune_suffixes=frozenset(suf))]


def _targeted_words(pair: str, c, *, cap: int = 400) -> list[str]:
    """The words this candidate actually TOUCHES — those bearing one of its member affixes. A what-if on a
    generic frequent sample shows ~0 change (those words are lexicalised); scoping the test to the affected
    words is what makes the before/after meaningful."""
    from review.reviewer_query import _word_freq
    pre, suf = _member_affixes(c)
    freq = _word_freq(pair)
    hits = [w for w in freq
            if (any(w.startswith(p) and len(w) > len(p) + 1 for p in pre)
                or any(w.endswith(s) and len(w) > len(s) + 1 for s in suf))]
    return sorted(hits, key=lambda w: -freq[w])[:cap]


def _what_if(pair: str, c) -> dict:
    """What-if on the candidate-TARGETED word set (words bearing its members)."""
    from review.reviewer_query import context, summarize
    opts = _whatif_options(pair, c)
    tw = _targeted_words(pair, c)
    if not opts or len(tw) < 5:
        return {}
    # untemplated so every option (incl. baseline) is on equal footing AND conditioned affixes parse right
    ctx = context(pair, test_words=tw, templated=False)
    return {"test_scope": f"{len(tw)} words bearing {sorted(set().union(*_member_affixes(c)))} (untemplated)",
            "options_simulated": [o.name for o in opts], **summarize(pair, opts, ctx)}


def dossier_view(c, *, pair: str = "", enrich: bool = False, whatif: bool = False) -> dict:
    """The evidence the reviewer is allowed to use — and nothing about the language not on this page."""
    r = c.rule if isinstance(c.rule, dict) else {}
    ev = r.get("evidence", {})
    support = ev.get("support") or {}
    n_support = sum(support.values()) if isinstance(support, dict) else 0
    # harmony/assimilation carry their conditioning as evidence={variant: {context: count}} — surface it
    # raw so the reviewer can see the actual distribution, not an empty collapse-shaped view.
    conditioning_evidence = ev if c.kind in ("harmony", "assimilation") else {}
    if not n_support and conditioning_evidence:        # harmony/assimilation support = sum of context counts
        for v in conditioning_evidence.values():
            if isinstance(v, dict):
                n_support += sum(n for n in v.values() if isinstance(n, int))
    sparsity = {"total_support": n_support, "sparse": 0 < n_support < 30,
                "note": "LOW SUPPORT — defer-for-data is appropriate" if 0 < n_support < 30 else ""}
    enriched = _enrich_glide(pair, c) if (enrich and pair and c.kind == "glide-collapse") else {}
    what_if = (_what_if(pair, c)
               if (whatif and pair and (c.score or 0) >= WHATIF_FLOOR) else {})
    return {
        "sparsity": sparsity,
        "enriched": enriched,
        "what_if": what_if,
        "id": c.id, "kind": c.kind, "claim": c.description, "members": c.members,
        "underlying": r.get("underlying", ""),
        "alternating": r.get("alternating", {}),
        "environment": r.get("environment", {}),
        "conditioning_evidence": conditioning_evidence,
        "distribution": {
            "meaning_similarity": ev.get("meaning_similarity"),
            "complementary_score": ev.get("complementary_score"),
            "support": ev.get("support"), "host_diversity": ev.get("host_diversity"),
            "env_profiles": ev.get("env_profiles"),
            "examples": ev.get("examples"), "english": ev.get("english"),
        },
        "mechanical_round_trip": {
            "recall": c.recall, "over_generation": c.over_gen, "support": c.support,
            "round_trip": r.get("round_trip"), "tolerance": r.get("tolerance"),
            "buildable": c.buildable, "auto_score": c.score,
        },
    }


def present(pair: str, *, enrich: bool = False, whatif: bool = False) -> list[dict]:
    views = [dossier_view(c, pair=pair, enrich=enrich, whatif=whatif) for c in build_dossiers(pair)]
    print(f"\n=== {pair}: {len(views)} candidate dossier(s) for Opus review "
          f"(decide from THIS evidence + universal method only) ===")
    for v in views:
        print(f"\n--- {v['id']}  [{v['kind']}] ---")
        print(f"  CLAIM: {v['claim']}")
        print(f"  members={v['members']}  UR=/{v['underlying']}/  alternating={v['alternating']}")
        print(f"  environment={v['environment']}")
        if v.get("conditioning_evidence"):
            print(f"  conditioning_evidence={v['conditioning_evidence']}")
        d = v["distribution"]
        print(f"  meaning_similarity={d['meaning_similarity']}  complementary={d['complementary_score']}  "
              f"support={d['support']}  hosts={d['host_diversity']}")
        if d.get("env_profiles"):
            print(f"  env_profiles={d['env_profiles']}")
        if d.get("examples"):
            print(f"  examples={d['examples']}")
        s = v.get("sparsity", {})
        print(f"  SPARSITY: total_support={s.get('total_support')} {s.get('note')}")
        m = v["mechanical_round_trip"]
        print(f"  ROUND-TRIP (blanket): recall={m['recall']} over_gen={m['over_generation']} "
              f"buildable={m['buildable']} tolerance={m['tolerance']}")
        e = v.get("enriched") or {}
        if e:
            print(f"  ENRICHED following-vowel: {e.get('following_vowel')}")
            print(f"  ENRICHED data-driven blockers: {e.get('data_driven_blockers')}")
            print(f"  ENRICHED conditioned round-trip: {e.get('conditioned_round_trip')}")
        wi = v.get("what_if") or {}
        if wi:
            b = wi["baseline"]
            print(f"  WHAT-IF  scope: {wi.get('test_scope')}")
            print(f"  WHAT-IF  before: coverage={b['coverage']} amb={b['amb']} parsed={b['n_parsed']}")
            shown = wi["options"][:3]                      # A, B, (sometimes) C — the top ranked guesses
            for o in shown:
                tag = chr(64 + o["rank"]) if o["rank"] <= 26 else str(o["rank"])
                print(f"  WHAT-IF  {tag} ({_ordinal(o['rank'])} guess) [{o['name']}]: coverage={o['coverage']} "
                      f"(d{o['delta']:+.4f}) gained={o['n_gained']} lost={o['n_lost']}  lost_eg={o['lost_examples'][:5]}")
            if len(wi["options"]) > len(shown):
                print(f"  WHAT-IF  (+{len(wi['options']) - len(shown)} lower-ranked hypotheses in JSON)")
            fn = wi.get("fit_neither")
            if fn:
                print(f"  WHAT-IF  fits NONE of the top {fn.get('over_top_k')}: {fn['n']} {fn['examples']}")
    return views


def _ordinal(k: int) -> str:
    return {1: "best", 2: "2nd", 3: "3rd"}.get(k, f"{k}th")


def apply_decisions(pair: str, decisions: dict) -> dict:
    """Apply Opus's decisions. A 'promote' is recorded; it is APPLIED to the gold only if the rule is also
    mechanically buildable (round-trips) — the gate backstops the reviewer. Returns a full report."""
    cands = build_dossiers(pair)
    rows, promoted_applied, promote_blocked = [], [], []
    for c in cands:
        dec = decisions.get(c.id, {})
        decision = dec.get("decision", "defer")
        rationale = dec.get("rationale", "not reviewed")
        c.classification = decision
        c.reason = f"opus-reviewer: {rationale}"
        # a glide-collapse is buildable if the DATA-DRIVEN CONDITIONED rule round-trips productively
        # (the blanket verify under-rates it); use the enriched grader for the gate.
        if c.kind == "glide-collapse" and decision == "promote":
            cond = _enrich_glide(pair, c).get("conditioned_round_trip", {})
            if cond.get("productive"):
                c.buildable = True
                c.rule["conditioned_rule"] = cond.get("rule")
        applied = False
        if decision == "promote":
            if c.buildable:
                promoted_applied.append(c); applied = True
            else:
                promote_blocked.append(c.id)         # Opus approved but the mechanical gate blocks it
        rows.append({"id": c.id, "kind": c.kind, "decision": decision, "applied": applied,
                     "buildable": c.buildable, "rationale": rationale, "auto_score": c.score})
    # apply the approved-AND-buildable rules (same path promote.run uses)
    _persist_collapse_rules(pair, [c for c in promoted_applied if c.kind == "glide-collapse"])
    activated = _promote_in_gold(pair, {c.id for c in promoted_applied})
    ops = _emit_delta_ops(pair, promoted_applied)
    return {"pair": pair, "reviewed": len(rows), "promoted_applied": [c.id for c in promoted_applied],
            "promote_blocked_by_gate": promote_blocked, "activated_in_gold": activated, "delta_ops": ops,
            "rows": rows}


def _emit_delta_ops(pair: str, promoted: list) -> int:
    from review.deltas.store import DeltaStore
    if not promoted:
        return 0
    store = DeltaStore.load(_RESEARCH / "deltas" / "store" / f"{pair}.deltas.jsonl")
    ops = []
    for c in promoted:
        op = _delta_op(c)
        op["provenance"] = {"source": "opus-reviewer", "pair": pair, "verify": c.score, "reason": c.reason}
        ops.append(op)
    n = store.add(ops)
    store.save()
    return n


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--apply", default="", help="path to DECISIONS.json to apply (omit to just present)")
    ap.add_argument("--enrich", action="store_true", help="add following-vowel + conditioned round-trip fields")
    ap.add_argument("--whatif", action="store_true", help="attach before/option-A/option-B/fit-neither what-if to every candidate >=20%% confident")
    ap.add_argument("--json", action="store_true", help="dump dossiers as JSON (for machine review)")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if a.apply:
        decisions = json.loads(Path(a.apply).read_text(encoding="utf-8"))
        r = apply_decisions(a.pair, decisions)
        print(f"\n[opus-review {a.pair}] reviewed {r['reviewed']}: "
              f"applied {r['promoted_applied']}, blocked-by-gate {r['promote_blocked_by_gate']}, "
              f"activated {r['activated_in_gold']} in gold, {r['delta_ops']} deltas")
        for row in r["rows"]:
            print(f"  [{row['decision']:7}{'*' if row['applied'] else ' '}] {row['id']}  {row['rationale'][:80]}")
        return 0
    if a.json:
        print(json.dumps([dossier_view(c, pair=a.pair, enrich=a.enrich, whatif=a.whatif)
                          for c in build_dossiers(a.pair)], ensure_ascii=False, indent=1))
    else:
        present(a.pair, enrich=a.enrich, whatif=a.whatif)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
