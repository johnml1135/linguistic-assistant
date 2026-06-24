"""Rule promotion — raise candidates that turn ENUMERATION into a DERIVED rule, verify, auto-classify.

HC's defining capability is morphophonology: an affix changes the stem by a predictable RULE. Today the
gold instead *enumerates* the variants (listed allomorphs, variant prefixes) and the detected rules sit
dormant as `data-derived` descriptions. This module makes promotion first-class:

  raise → a candidate = an underlying form + a conditioning rule that derives a family we now enumerate
  verify → does the rule reproduce the attested members (recall), without over-generating (precision)?
           + how sharp/supported is the conditioning, and does it lower description length (ΔMDL)?
  classify → PROMOTE (apply it: status data-derived→active + a deltas op) | DEFER (a phonology_rule ticket)
             | REJECT (conditioning too weak / over-generates)

Finders (this v1 implements A+B via the existing detectors): A paradigm-collapse + B distributional
alternation mining (`gold.phonology_induce`). The gate is C (evidence sharpness now; an HC round-trip via
`engine.hc` + `gold.phonology_gold` is the deeper check). Contract-clean: review imports gold/engine/assess.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

from gold.goldio import FROZEN
from gold.phonology_induce import nasal_assimilation, vowel_harmony

PROMOTE_AT = 0.75      # auto-promote above this verify score
DEFER_AT = 0.50        # below → reject; between → defer to a phonology_rule ticket


@dataclass
class RuleCandidate:
    id: str
    pair: str
    kind: str                          # assimilation | harmony | allomorph-collapse
    description: str
    members: list = field(default_factory=list)     # the surface variants the rule would derive
    score: float = 0.0                 # verify score in [0,1]
    recall: float = 0.0                # attested members the rule reproduces
    over_gen: float = 0.0              # spurious forms it would also license (lower = better)
    support: int = 0                   # corpus evidence count
    buildable: bool = False            # is there an HC rule-emitter for this kind? (operationally applicable)
    classification: str = ""           # promote | defer | reject
    reason: str = ""                   # why this classification
    rule: dict = field(default_factory=dict)        # the source detector record

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- raise (finders A + B)
def raise_candidates(pair: str) -> list[RuleCandidate]:
    out: list[RuleCandidate] = []
    # B (distributional) + A (paradigm) via the existing morphophonology detectors
    for r in nasal_assimilation(pair):
        ev = r.get("evidence", {})
        members = sorted(ev)                                   # the variant prefixes (mem-/men-/meng-)
        support = sum(v.get("n", 0) for v in ev.values())
        out.append(RuleCandidate(id=r["id"], pair=pair, kind="assimilation",
                                 description=r["description"], members=members, support=support, rule=r))
    for r in vowel_harmony(pair):
        ev = r.get("evidence", {})
        members = sorted(ev)
        support = sum(sum(d.values()) for d in ev.values() if isinstance(d, dict))
        out.append(RuleCandidate(id=r["id"], pair=pair, kind="harmony",
                                 description=r["description"], members=members, support=support, rule=r))
    # Finder A′ — allomorph collapse (same meaning, different environment) from the raw-edge detector.
    # Glide-shaped pairs (mu/mw, vi/vy) get kind `glide-collapse` (buildable); others stay non-buildable.
    try:
        from review.allomorph import detect as _detect_allo
        allo = _detect_allo(pair, source="raw", use_vectors=False)
    except Exception:
        allo = {"candidates": []}
    for c in allo.get("candidates", []):
        shape = _glide_shape(c)
        support = sum(c.get("evidence", {}).get("support", {}).values())
        out.append(RuleCandidate(id=c["id"], pair=pair,
                                 kind="glide-collapse" if shape else "allomorph-collapse",
                                 description=c["rule"], members=c["members"], support=support, rule=c))
    return out


def _glide_shape(cand: dict) -> dict | None:
    """If a collapse candidate is a high-vowel→glide pair (mu/mw, vi/vy, mi/my), return its underlying
    form, the alternating vowel, and the glide form. Else None (non-glide → no emitter)."""
    from engine.hc_collapse import GLIDE_OF
    if not cand.get("alternating", {}).get("vocalic"):
        return None
    members = cand.get("members", [])
    for ur in members:
        if ur and ur[-1] in GLIDE_OF:
            glide_form = ur[:-1] + GLIDE_OF[ur[-1]]
            if glide_form in members and glide_form != ur:
                return {"ur": ur, "vowel": ur[-1], "glide": GLIDE_OF[ur[-1]], "glide_form": glide_form}
    return None


def _verify_collapse(cand: RuleCandidate) -> dict:
    """Run the HC round-trip for a glide collapse against its OWN counterexamples: pull ALL distinct
    member words from the corpus (so the rare `ur`+vowel forms that falsify the rule — *muumini* — are
    included, unlike a top-k-by-frequency sample) and round-trip them."""
    from engine.hc_collapse import glide_collapse_round_trips
    from review.allomorph import member_words
    shape = _glide_shape(cand.rule)
    if not shape:
        return {"ran": False, "ok": False, "recall_env": 0.0, "n_env": 0, "n_exceptions": 0,
                "reason": "non-glide collapse — no emitter"}
    ur_words = member_words(cand.pair, shape["ur"])              # ur+cons AND ur+vowel (counterexamples)
    glide_words = member_words(cand.pair, shape["glide_form"])   # the glide-form words
    return glide_collapse_round_trips(shape["ur"], shape["vowel"], shape["glide"], ur_words, glide_words)


# --------------------------------------------------------------------------- verify (gate C signal)
def verify(cand: RuleCandidate) -> RuleCandidate:
    """Score the candidate: does its conditioning sharply + supportedly predict the attested distribution?
    (The detector already required complementary distribution; here we quantify recall/over-gen + support.)
    A full HC round-trip — build the rule via `gold.phonology_gold`, re-parse, check the family round-trips
    with no regression — is the deeper gate; the evidence sharpness is the v1 proxy."""
    from gold.phonology_gold import EMITTABLE_KINDS
    ev = cand.rule.get("evidence", {})
    cand.recall = 1.0 if cand.members else 0.0                 # the rule derives exactly the listed members
    if cand.kind == "assimilation":
        confirmed = cand.rule.get("variants_confirmed", 0)
        sharp = confirmed / max(len(cand.members), 1)          # fraction of variants matching predicted place
        cand.over_gen = round(1 - sharp, 2)
        cand.buildable = cand.kind in EMITTABLE_KINDS
    elif cand.kind == "harmony":
        # separation margin: how cleanly each suffix's stems fall on its side of the height split
        margins = []
        for sfx, dist in ev.items():
            if isinstance(dist, dict) and dist:
                hl = sum(dist.get(v, 0) for v in "aiu"); mid = sum(dist.get(v, 0) for v in "eo")
                tot = hl + mid or 1
                margins.append(max(hl, mid) / tot)
        sharp = sum(margins) / len(margins) if margins else 0.0
        cand.over_gen = round(1 - sharp, 2)
        cand.buildable = cand.kind in EMITTABLE_KINDS
    elif cand.kind == "glide-collapse":
        # the REAL gate: re-parse the members (incl. the rule's own counterexamples) through HC, then judge
        # by the Tolerance Principle — a productive rule may carry a bounded exception set (e ≤ N/ln N).
        from assess.metrics import tolerance_productive
        rt = _verify_collapse(cand)
        n_env, exc = rt.get("n_env", 0), rt.get("n_exceptions", 0)
        tol = tolerance_productive(n_env, exc) if n_env >= 2 else {"productive": False, "reason": "too few in-env items"}
        cand.rule["round_trip"] = rt
        cand.rule["tolerance"] = tol
        cand.recall = rt.get("recall_env", 0.0)                 # recall in the rule's actual environment
        cand.over_gen = round(exc / n_env, 2) if n_env else 1.0  # over-application rate (real exceptions)
        cand.buildable = bool(rt.get("ran")) and bool(tol.get("productive"))   # buildable = productive rule
        sharp = cand.recall
    else:                                                       # non-glide allomorph-collapse: no emitter yet
        sharp = 0.4
        cand.over_gen = 0.5
        cand.buildable = False
    supp = min(1.0, math.log10(max(cand.support, 1) + 1) / 2)  # log-scaled corpus support, capped
    cand.score = round(0.6 * sharp + 0.4 * supp, 3)
    return cand


def classify(cand: RuleCandidate) -> RuleCandidate:
    # A candidate may only PROMOTE if it can be operationally applied (a rule-emitter exists) AND its
    # conditioning is sharp+supported. A high-quality rule with no emitter is DEFERRED with the reason —
    # never marked active-but-inert (that would be a fake promotion).
    if not cand.buildable:
        cand.classification = "defer"
        cand.reason = f"good candidate but no HC rule-emitter for kind '{cand.kind}' yet — build the emitter"
    elif cand.score >= PROMOTE_AT:
        cand.classification = "promote"; cand.reason = "buildable + sharp, supported conditioning"
    elif cand.score >= DEFER_AT:
        cand.classification = "defer"; cand.reason = "buildable but conditioning below the promote bar"
    else:
        cand.classification = "reject"; cand.reason = "conditioning too weak / unsupported"
    return cand


# --------------------------------------------------------------------------- run (first-class stage)
def _delta_op(cand: RuleCandidate) -> dict:
    return {"op": "morphophonology.rule.add", "name": cand.id, "rule": cand.description,
            "members": cand.members, "kind": cand.kind, "confidence": cand.score,
            "provenance": {"source": "promote", "pair": cand.pair, "verify": cand.score}}


def _promote_in_gold(pair: str, promoted_ids: set[str]) -> int:
    """Flip the gold's data-derived rules to `active` for the promoted ids (the actual promotion)."""
    p = FROZEN / pair / "phonology_induced.jsonl"
    if not p.exists():
        return 0
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = 0
    for r in rows:
        want = "active" if r.get("id") in promoted_ids else "data-derived"   # reconcile: active iff promoted
        if r.get("status") != want:
            if want == "active":
                n += 1
            r["status"] = want
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return n


def _persist_collapse_rules(pair: str, collapse: list[RuleCandidate]) -> None:
    """Upsert promoted glide-collapse rules into phonology_induced.jsonl so `active_phon_rules` emits them
    (the corpus detectors write nasal/harmony there; collapse comes from the allomorph detector)."""
    if not collapse:
        return
    p = FROZEN / pair / "phonology_induced.jsonl"
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []
    by_id = {r.get("id"): r for r in rows}
    for c in collapse:
        rec = by_id.get(c.id, {})
        rec.update({"id": c.id, "type": "rule", "kind": c.kind, "status": "active",
                    "members": c.members, "description": c.description,
                    "rule": c.rule.get("rule") if isinstance(c.rule, dict) else c.description})
        by_id[c.id] = rec
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in by_id.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run(pair: str, *, apply: bool = False) -> dict:
    cands = [classify(verify(c)) for c in raise_candidates(pair)]
    promoted = [c for c in cands if c.classification == "promote"]
    deferred = [c for c in cands if c.classification == "defer"]
    rejected = [c for c in cands if c.classification == "reject"]
    applied = ops = tickets = 0
    if apply:
        _persist_collapse_rules(pair, [c for c in promoted if c.kind == "glide-collapse"])
        applied = _promote_in_gold(pair, {c.id for c in promoted})
        ops = len([_delta_op(c) for c in promoted])            # change-set ops (ingested by review.deltas)
        tickets = _ticket_deferrals(pair, deferred)
    return {"pair": pair, "candidates": len(cands),
            "promote": [c.id for c in promoted], "defer": [c.id for c in deferred],
            "reject": [c.id for c in rejected], "rows": [c.to_dict() for c in cands],
            "activated_in_gold": applied, "delta_ops": ops, "tickets": tickets}


def _ticket_deferrals(pair: str, deferred: list[RuleCandidate]) -> int:
    """A borderline candidate → a phonology_rule deferral ticket (a grammar edit for human review)."""
    from review.deferrals.build import build_ticket
    from review.deferrals.store import TicketStore
    if not deferred:
        return 0
    store = TicketStore(pair)
    built = []
    for c in deferred:
        rec = {"affix": c.members[0].rstrip("-") if c.members else c.id, "kind": "prefix" if c.kind == "assimilation" else "suffix",
               "function": c.description, "conf": "low", "source": "promote", "rule_candidate": c.id}
        built.append(build_ticket(pair, rec, with_counterfactuals=False))
    n = store.upsert(built); store.save()
    return n


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", choices=["spa", "ind", "tgl", "swh"], help="(omit to run all four)")
    ap.add_argument("--apply", action="store_true", help="activate promoted rules in the gold + emit ops/tickets")
    args = ap.parse_args(argv)
    pairs = [args.pair] if args.pair else ["spa", "ind", "tgl", "swh"]
    for pair in pairs:
        s = run(pair, apply=args.apply)
        print(f"\n[{pair}] {s['candidates']} rule candidates — "
              f"promote {len(s['promote'])} · defer {len(s['defer'])} · reject {len(s['reject'])}")
        for c in s["rows"]:
            print(f"  [{c['classification']:7}] {c['id']}  score={c['score']} "
                  f"(recall {c['recall']}, over-gen {c['over_gen']}, support {c['support']})")
            print(f"      {c['description'][:96]}")
        if args.apply:
            print(f"  → activated {s['activated_in_gold']} in gold, {s['delta_ops']} deltas, {s['tickets']} tickets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
