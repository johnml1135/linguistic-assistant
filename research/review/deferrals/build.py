"""Deterministic package builder (Phase A) — assemble a complete `DeferralTicket` with no LLM.

Wires the pieces: the taxonomy (`taxonomy.enumerate_hypotheses`) → the HC counterfactual engine
(`counterfactual.attach_counterfactuals`) → 5–10 scripted speaker questions selected + slot-filled from
`parsegym.questions` → impact / confidence tags computed from the corpus + gold → a templated
`context_md` so the ticket is readable offline. `build_ticket` produces one schema-valid ticket;
`build_all` backfills a list of defer records and links their dependencies.
"""

from __future__ import annotations

from collections import Counter

from eval.parsegym import questions as Q

from engine.grammar import LangModel
from gold.goldio import load_gold

import json

from gold.goldio import FROZEN

from . import counterfactual as CF
from .schema import DeferralTicket, Hypothesis, PresentationOption, Resolution
from .taxonomy import _nearest_lemma, enumerate_hypotheses, followon_stubs

LANG_NAME = {"spa": "Spanish", "ind": "Indonesian", "tgl": "Tagalog", "swh": "Swahili"}

# question archetypes worth offering per ticket type, best-first (the catalogue is in parsegym.questions)
_QUESTIONS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "lexeme_gloss": ("elicit_meaning", "meaning_choice", "elicit_form", "allomorph_check",
                     "minimal_pair", "segmentation", "frame_completion", "grammaticality"),
    "homograph": ("meaning_choice", "frame_completion", "contrast_function", "acceptability_rank",
                  "grammaticality", "minimal_pair"),
    "affix_function": ("contrast_function", "paradigm_fill", "agreement_probe", "segmentation",
                       "minimal_pair", "grammaticality", "acceptability_rank"),
    "segmentation": ("segmentation", "contrast_function", "minimal_pair", "allomorph_check",
                     "grammaticality", "frame_completion"),
    "phonology_rule": ("minimal_pair", "allomorph_check", "acceptability_rank", "grammaticality"),
    "pos": ("frame_completion", "contrast_function", "paradigm_fill", "grammaticality", "meaning_choice"),
}


def _slot_values(pair: str, rec: dict, gold: dict, hyps: list[Hypothesis]) -> dict:
    """Best-effort fillers for the question templates; a question whose slots aren't all available is
    simply skipped, so this can be generous."""
    word = (rec.get("word") or rec.get("affix") or "").lstrip("-").rstrip("-").lower()
    glosses = list(dict.fromkeys(g for g in (rec.get("gloss"), rec.get("aligner_top1"),
                                             *(rec.get("candidates") or [])) if g))
    near = _nearest_lemma(word, gold.get("lemmas", []))
    # a stem from a resegment hypothesis, if any
    stem = ""
    for h in hyps:
        for e in h.edits:
            if e.kind == "resegment":
                for sub in e.params.get("edits", []):
                    if (sub.get("params") or {}).get("form"):
                        stem = sub["params"]["form"]
    options = ", ".join(f"‘{g}’" for g in glosses[:6]) or f"‘{word}’"
    vals = {
        "form": word, "language": LANG_NAME.get(pair, pair),
        "english": glosses[0] if glosses else word, "options": options,
        "lemma": near or word, "gloss": glosses[0] if glosses else word,
        "feature": "a different person, number, or tense",
        "part": rec.get("affix", "").lstrip("-").rstrip("-") or (word[-2:] if len(word) > 2 else word),
        "base": near or stem or word, "derived": word,
        "a": word, "b": near or stem or word, "frame": "",
    }
    return vals


def select_options(pair: str, ttype: str, rec: dict, gold: dict, hyps: list[Hypothesis],
                   *, lo: int = 5, hi: int = 10) -> list[PresentationOption]:
    """Pick 5–10 scripted speaker questions for the ticket, slot-filled and tagged with which
    hypotheses each one discriminates."""
    vals = _slot_values(pair, rec, gold, hyps)
    chosen: list[PresentationOption] = []
    qids = list(_QUESTIONS_BY_TYPE.get(ttype, _QUESTIONS_BY_TYPE["lexeme_gloss"]))
    # also pull in any question a hypothesis explicitly says it is discriminated by, in case the
    # type list omits it
    for h in hyps:
        for qid in h.discriminates:
            if qid not in qids:
                qids.append(qid)
    n = 0
    for qid in qids:
        if len(chosen) >= hi:
            break
        try:
            q = Q.get(qid)
            text = q.render(**vals)
        except KeyError:
            continue                                   # a slot we can't fill → skip this archetype
        if not text or "{" in text:
            continue
        n += 1
        discr = [h.id for h in hyps if qid in h.discriminates]
        chosen.append(PresentationOption(id=f"o{n}", question_id=qid, kind=q.kind, text=text,
                                         discriminates=discr))
    return chosen


def compute_impact(pair: str, form: str, gold: dict) -> dict:
    """Impact = corpus frequency of the form × the number of related wordforms a fix would newly affect
    (forms sharing its stem). Bucketed into a priority for triage."""
    freqs = CF._freqs(pair)
    freq = freqs.get(form.lower(), 0)
    related = [w for w in freqs if CF._shares_stem(form.lower(), w)]
    wordforms = len(related)
    affected_freq = sum(freqs.get(w, 0) for w in related)
    score = affected_freq
    priority = "high" if score >= 200 else "medium" if score >= 30 else "low"
    return {"freq": freq, "wordforms": wordforms, "affected_freq": affected_freq,
            "score": score, "priority": priority}


def compute_confidence(rec: dict, hyps: list[Hypothesis]) -> float:
    """A coarse [0,1] confidence: source confidence + aligner agreement + hypothesis-margin.

    More candidate hypotheses → lower confidence (the decision is less determined); an explicit high
    source confidence or aligner agreement raises it."""
    base = {"high": 0.8, "medium": 0.55, "low": 0.3}.get(str(rec.get("conf")), 0.4)
    if rec.get("aligner_top1") and rec.get("gloss") and \
            rec["aligner_top1"].lower() in str(rec["gloss"]).lower():
        base = min(1.0, base + 0.1)
    margin = 0.0 if len(hyps) <= 1 else -0.05 * (len(hyps) - 1)
    return round(max(0.0, min(1.0, base + margin)), 3)


def _context_md(pair: str, rec: dict, ttype: str, hyps: list[Hypothesis], impact: dict) -> str:
    """A templated (LLM-free) human narrative, so Phase A tickets are complete offline."""
    word = rec.get("word") or rec.get("affix") or "?"
    cur = rec.get("current_gold")
    lines = [
        f"**{LANG_NAME.get(pair, pair)}** — a *{ttype.replace('_', ' ')}* decision is needed for "
        f"**“{word}”**.",
        "",
        f"The automatic pipeline deferred this (it would not guess). Current gold: "
        f"{('‘' + str(cur) + '’') if cur else '— (none)'}.",
        f"Impact: appears in ~{impact['wordforms']} related wordforms "
        f"(priority **{impact['priority']}**).",
        "",
        f"{len(hyps)} hypothesis(es) were generated; each shows how scripture would re-parse if it were "
        f"true. Pick the correct one, accept it with extra forms, or reject all with a reason.",
    ]
    return "\n".join(lines)


def _ticket_id(pair: str, rec: dict, ttype: str) -> str:
    key = (rec.get("word") or rec.get("affix") or "x").lstrip("-").rstrip("-")
    return f"{pair}-{ttype}-{key}"


def build_ticket(pair: str, rec: dict, *, gold: dict | None = None, base: LangModel | None = None,
                 pf: dict | None = None, allowed: set[str] | None = None, profile=None,
                 with_counterfactuals: bool = True) -> DeferralTicket:
    """Build one complete, schema-valid `DeferralTicket` from a defer record. Deterministic, LLM-free.

    The language profile (loaded if not supplied) constrains the hypothesis space (locked-off affix
    processes / edit kinds are pruned) and sets the per-language auto-accept bar recorded on the ticket."""
    gold = gold or load_gold(pair)
    if profile is None:
        from . import profile as P
        profile = P.load(pair)
    allowed = allowed if allowed is not None else profile.allowed_edit_kinds()
    ttype, domain, hyps = enumerate_hypotheses(rec, gold, allowed=allowed,
                                               allowed_affix_kinds=profile.allowed_affix_kinds())
    form = (rec.get("word") or rec.get("affix") or "").lstrip("-").rstrip("-").lower()

    if with_counterfactuals and hyps:
        CF.attach_counterfactuals(pair, hyps, form, base=base, pf=pf)
    # documented follow-on stubs (reduplication / concord / compounding) — flagged, never silently dropped
    hyps = list(hyps) + followon_stubs(form, profile)
    edge_cases = _discriminating_forms(hyps)

    impact = compute_impact(pair, form, gold)
    options = select_options(pair, ttype, rec, gold, hyps)
    confidence = compute_confidence(rec, hyps)
    target = {"form": form, **{k: rec.get(k) for k in ("gloss", "pos", "aligner_top1", "current_gold",
                                                       "function", "feature", "kind") if rec.get(k) is not None}}
    t = DeferralTicket(
        id=_ticket_id(pair, rec, ttype), pair=pair, type=ttype, domain=domain, status="open",
        target=target, confidence=confidence, impact=impact, dependencies=[],
        context_md=_context_md(pair, rec, ttype, hyps, impact), hypotheses=hyps,
        presentation_options=options, resolution=Resolution(),
        tags={"domain": domain, "impact": impact["priority"], "source": rec.get("source", "defer"),
              "auto_accept_bar": profile.auto_accept_bar(), "morph_type": profile.morph_type,
              "edge_cases": edge_cases},
        provenance={"defer_record": {k: rec.get(k) for k in ("word", "affix", "conf", "decision")}},
    )
    t.validate()
    return t


def _discriminating_forms(hyps: list[Hypothesis], cap: int = 6) -> list[str]:
    """Edge-case selection (D12 / task 14.3): the forms the live hypotheses parse DIFFERENTLY — the
    minimal pairs worth showing the reviewer, not arbitrary examples. Computed from the counterfactuals."""
    per_hyp: dict[str, dict[str, frozenset]] = {}
    for h in hyps:
        seen: dict[str, frozenset] = {}
        for cf in h.counterfactuals:
            for w, analyses in cf.if_hyp.items():
                seen[w] = frozenset(tuple(a) for a in analyses)
        per_hyp[h.id] = seen
    words = {w for s in per_hyp.values() for w in s}
    disc = [w for w in words if len({per_hyp[hid].get(w, frozenset()) for hid in per_hyp}) > 1]
    return sorted(disc)[:cap]


def link_dependencies(tickets: list[DeferralTicket]) -> list[DeferralTicket]:
    """Fill `dependencies`: tickets sharing a lemma/affix/stem reference each other (advisory ordering)."""
    by_stem: dict[str, list[str]] = {}
    for t in tickets:
        stem = (t.target.get("form") or "")[:4]
        by_stem.setdefault(stem, []).append(t.id)
    for t in tickets:
        stem = (t.target.get("form") or "")[:4]
        t.dependencies = sorted(tid for tid in by_stem.get(stem, []) if tid != t.id)
    return tickets


def build_all(pair: str, records: list[dict], *, allowed: set[str] | None = None,
              with_counterfactuals: bool = True) -> list[DeferralTicket]:
    """Backfill tickets from many defer records (shared gold/base load), then link dependencies."""
    from . import profile as P
    gold = load_gold(pair)
    profile = P.load(pair)
    base = pf = None
    if with_counterfactuals:
        base, pf = CF.load_base(pair)
    tickets = [build_ticket(pair, r, gold=gold, base=base, pf=pf, allowed=allowed, profile=profile,
                            with_counterfactuals=with_counterfactuals) for r in records]
    return link_dependencies(tickets)


def load_defer_records(pair: str) -> list[dict]:
    """Collect existing `defer` records for a pair: deferred lexical proposals + deferred affix functions."""
    frozen = FROZEN / pair
    recs: list[dict] = []
    lex = frozen / "gemma_proposals.jsonl"
    if lex.exists():
        for line in lex.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("decision") == "defer":
                    recs.append({**r, "source": "propose.py"})
    aff = frozen / "gemma_affix_proposals.jsonl"
    if aff.exists():
        for line in aff.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("conf") != "high":            # not auto-accepted → deferred
                    recs.append({**r, "source": "propose_morph"})
    return recs


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .store import TicketStore

    ap = argparse.ArgumentParser(description="Backfill deferral tickets from existing defer records.")
    ap.add_argument("--pair", required=True, choices=list(LANG_NAME))
    ap.add_argument("--limit", type=int, default=0, help="cap records (0 = all)")
    ap.add_argument("--no-hc", action="store_true", help="skip HC counterfactuals (fast, offline)")
    args = ap.parse_args(argv)

    records = load_defer_records(args.pair)
    if args.limit:
        records = records[: args.limit]
    if not records:
        print(f"[{args.pair}] no defer records found (run propose.py first).")
        return 0
    tickets = build_all(args.pair, records, with_counterfactuals=not args.no_hc)
    store = TicketStore(args.pair)
    new = store.upsert(tickets)
    store.save()
    by_type: Counter = Counter(t.type for t in tickets)
    print(f"[{args.pair}] built {len(tickets)} tickets ({new} new) → {store.path}")
    print(f"  by type: {dict(by_type)}")
    for t in store.list()[:8]:
        print(f"    {t.impact['priority']:6} {t.id:34} {len(t.hypotheses)} hyp, "
              f"{len(t.presentation_options)} options")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
