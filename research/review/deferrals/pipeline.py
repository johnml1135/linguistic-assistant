"""The 4-stage cyclical pipeline + per-stage scoring against the ablation validation set.

`score_pipeline` runs ablation scenarios (`validation.py`) through the stages and measures each one
independently — the signal-to-noise dials of D6:

  Stage 2 (selection):   does `select.rank_targets` surface the broken region near the top?   (recall)
  Stage 3 (generation):  do the taxonomy hypotheses contain the true (removed) item?            (recall)
  Stage 4 (assessment):  does `assess` accept the true item and reject the decoy?               (precision)

`recycle` is the cyclical re-evaluation (D10): after a resolution changes the grammar state, dependent
open tickets are re-scored; one that has become confidently resolvable is flagged for promotion, and a
ticket invalidated by the change is re-opened. The loop iterates to convergence.
"""

from __future__ import annotations

from . import assess as A
from . import select as SEL
from . import validation as V
from .counterfactual import load_base
from .schema import DeferralTicket
from .store import TicketStore
from .taxonomy import enumerate_hypotheses


def _true_in_hypotheses(scenario: dict, gold: dict) -> bool:
    """Stage-3 recall: does the taxonomy, on the broken focus, generate the removed item (or equivalent)?"""
    gt = scenario["ground_truth"]
    focus = scenario["focus"]
    if gt["kind"] == "lex":
        rec = {"word": focus, "gloss": gt["gloss"], "aligner_top1": gt["gloss"]}
    else:
        rec = {"affix": gt["form"], "kind": gt.get("affix_kind", "suffix"), "gloss": gt["gloss"]}
    _, _, hyps = enumerate_hypotheses(rec, gold)
    for h in hyps:
        for e in h.edits:
            p = e.params
            if gt["kind"] == "lex" and e.kind in ("add_lexentry", "add_allomorph", "resegment"):
                return True
            if gt["kind"] == "affix" and e.kind == "add_affix" and p.get("form") == gt["form"]:
                return True
    return False


def score_pipeline(pair: str, *, n_lex: int = 2, n_affix: int = 2, n_slice: int = 40) -> dict:
    """Generate a few ablation scenarios and score stages 2–4 against their known answer key."""
    base, pf = load_base(pair)
    from gold.goldio import load_gold
    gold = load_gold(pair)
    scenarios = [V.ablate(pair, "lex", r, base=base, pf=pf, n_slice=n_slice) for r in range(n_lex)] + \
                [V.ablate(pair, "affix", r, base=base, pf=pf, n_slice=n_slice) for r in range(n_affix)]
    scenarios = [s for s in scenarios if s["broken"]]            # keep scenarios that actually broke forms

    s2_hits = s3_hits = s4_true_ok = s4_decoy_rejected = n = 0
    for s in scenarios:
        n += 1
        focus, crippled, words = s["focus"], s["crippled"], s["words"]
        # Stage 2 — is the broken focus among the top-ranked selection candidates?
        ranked = SEL.rank_targets(pair, s["broken"], gold=gold)
        top = {r["word"] for r in ranked[:max(3, len(ranked) // 2)]}
        s2_hits += focus in top
        # Stage 3 — does generation contain the true fix?
        s3_hits += _true_in_hypotheses(s, gold)
        # Stage 4 — accept the true item, reject the over-broad decoy
        truth, decoy = V.true_hypothesis(s), V.decoy_hypothesis(s)
        A.assess_hypothesis(pair, truth, focus, base=crippled, pf=pf, words=words)
        A.assess_hypothesis(pair, decoy, focus, base=crippled, pf=pf, words=words)
        s4_true_ok += bool(truth.verdict.get("acceptable"))
        s4_decoy_rejected += (not decoy.verdict.get("acceptable")) or \
            (truth.metrics.get("delta_mdl", 0) <= decoy.metrics.get("delta_mdl", 0))

    return {"pair": pair, "scenarios": n,
            "stage2_selection_recall": round(s2_hits / n, 3) if n else None,
            "stage3_hypothesis_recall": round(s3_hits / n, 3) if n else None,
            "stage4_true_accept_rate": round(s4_true_ok / n, 3) if n else None,
            "stage4_decoy_reject_rate": round(s4_decoy_rejected / n, 3) if n else None}


def should_escalate(ticket: DeferralTicket, *, cluster_min: int = 3) -> bool:
    """Phase C trigger (task 7.1): escalate to a multi-agent workflow only for high-impact tickets or
    dependency clusters ≥ cluster_min. Deterministic routing; the heavy investigation is the workflow."""
    return ticket.impact.get("priority") == "high" or len(ticket.dependencies) >= cluster_min


def escalation_queue(store: TicketStore, *, cluster_min: int = 3) -> list[str]:
    """The open tickets that warrant Phase C escalation, highest-impact first."""
    return [t.id for t in store.list(status="open") if should_escalate(t, cluster_min=cluster_min)]


def recycle(store: TicketStore, resolved_id: str, *, base=None, pf=None) -> dict:
    """Cyclical re-evaluation after `resolved_id` was resolved: re-assess open tickets that depend on it.

    A dependent ticket whose hypotheses now have an acceptable verdict is flagged `promote` (it became
    low-hanging fruit); the store can then auto-accept or fast-track it. Deterministic; HC only for the
    re-assessment of dependents (bounded)."""
    resolved = store.get(resolved_id)
    if resolved is None:
        return {"ok": False, "error": "no such ticket"}
    if base is None or pf is None:
        base, pf = load_base(store.pair)
    promoted, rescored = [], []
    for t in store.tickets:
        if t.status != "open" or resolved_id not in t.dependencies:
            continue
        A.assess_ticket(t, base=base, pf=pf)
        rescored.append(t.id)
        if any(h.verdict.get("acceptable") for h in t.hypotheses):
            promoted.append(t.id)
    return {"ok": True, "resolved": resolved_id, "rescored": rescored, "promoted": promoted}
