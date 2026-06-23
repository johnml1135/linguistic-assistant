"""The tracked ticket store + bug-tracker lifecycle + `deltas/` write-back.

Tickets live in `deferrals/<pair>/tickets.jsonl` (git-tracked, one record per line, like the gold). The
store loads/saves them, drives the status lifecycle (open → in_review → resolved | wont_fix), and exposes
list/sort/filter by status/domain/impact/dependency order. A non-reject resolution maps the chosen
hypothesis's typed edits into `deltas/` change-set ops (confidence-routed + locked as a human decision),
so accepted answers reach the gold only through the existing applier — never by mutating it here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review.deltas.store import DeltaStore  # noqa: E402
from propose.change_set import op_signature  # noqa: E402

from .schema import DeferralTicket, Hypothesis, Resolution, read_jsonl, write_jsonl  # noqa: E402

DEFERRALS = _RESEARCH / "deferrals"
DELTA_STORE = _RESEARCH / "deltas" / "store"

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def store_path(pair: str) -> Path:
    return DEFERRALS / pair / "tickets.jsonl"


class TicketStore:
    """Load/modify/save the per-pair ticket JSONL with a status lifecycle."""

    def __init__(self, pair: str, path: Path | None = None, delta_dir: Path | None = None):
        self.pair = pair
        self.path = Path(path) if path else store_path(pair)
        self.delta_dir = Path(delta_dir) if delta_dir else DELTA_STORE
        self.tickets: list[DeferralTicket] = read_jsonl(self.path)
        self._by_id = {t.id: t for t in self.tickets}

    # ---- persistence ---------------------------------------------------------------------------
    def save(self) -> int:
        return write_jsonl(self.tickets, self.path)

    def upsert(self, tickets: list[DeferralTicket]) -> int:
        """Add new tickets / replace existing ones by id. Returns the count of NEW ids."""
        new = 0
        for t in tickets:
            if t.id not in self._by_id:
                self.tickets.append(t)
                new += 1
            else:
                self.tickets[self.tickets.index(self._by_id[t.id])] = t
            self._by_id[t.id] = t
        return new

    def get(self, ticket_id: str) -> DeferralTicket | None:
        return self._by_id.get(ticket_id)

    # ---- lifecycle -----------------------------------------------------------------------------
    def _transition(self, t: DeferralTicket, to: str, by: str) -> None:
        t.history.append({"from": t.status, "to": to, "by": by})
        t.status = to

    def start_review(self, ticket_id: str, by: str = "human") -> bool:
        t = self.get(ticket_id)
        if t and t.status == "open":
            self._transition(t, "in_review", by)
            return True
        return False

    def reopen(self, ticket_id: str, by: str = "system") -> bool:
        """Re-open an invalidated/superseded ticket (cyclical re-evaluation)."""
        t = self.get(ticket_id)
        if t and t.status in ("resolved", "wont_fix"):
            self._transition(t, "open", by)
            t.resolution = Resolution()
            return True
        return False

    # ---- listing -------------------------------------------------------------------------------
    def list(self, *, status: str | None = None, domain: str | None = None) -> list[DeferralTicket]:
        ts = [t for t in self.tickets
              if (status is None or t.status == status) and (domain is None or t.domain == domain)]
        # priority order: impact bucket, then raw impact score, then dependency-light first
        return sorted(ts, key=lambda t: (_PRIORITY_RANK.get(t.impact.get("priority"), 3),
                                         -t.impact.get("score", 0), len(t.dependencies), t.id))

    def suggested_order(self) -> list[DeferralTicket]:
        """Advisory resolution order: unblocking (fewer dependencies) + higher impact first."""
        return self.list(status="open")

    # ---- resolution + ledger write-back --------------------------------------------------------
    def resolve(self, ticket_id: str, resolution: Resolution, *, accept_at: float = 0.85) -> dict:
        """Apply a reviewer's single resolution. On a non-reject action, emit confidence-routed,
        human-locked `deltas/` ops for the chosen hypothesis's edits. Returns a summary."""
        t = self.get(ticket_id)
        if t is None:
            return {"ok": False, "error": "no such ticket"}
        resolution.validate()
        ops: list[dict] = []
        if resolution.action in ("accept_option", "accept_with_words"):
            hyp = next((h for h in t.hypotheses if h.id == resolution.hypothesis_id), None)
            if hyp is None:
                return {"ok": False, "error": f"no hypothesis {resolution.hypothesis_id}"}
            ops = edits_to_ops(t, hyp, resolution.extra_words)
            resolution.delta_ops = ops
            applied = _write_deltas(self.pair, ops, accept_at=accept_at, delta_dir=self.delta_dir)
            self._transition(t, "resolved", resolution.by or "human")
        else:  # reject_with_reason
            applied = {"added": 0, "accepted": 0}
            self._transition(t, "wont_fix", resolution.by or "human")
        t.resolution = resolution
        return {"ok": True, "ticket": t.id, "status": t.status, "ops": len(ops), "ledger": applied}


# ---- hypothesis-edit → change-set op mapping ---------------------------------------------------
def _entry_id(pair: str, form: str) -> str:
    return f"entry:{pair}:{form}"


def edits_to_ops(ticket: DeferralTicket, hyp: Hypothesis, extra_words: list | None = None) -> list[dict]:
    """Map a hypothesis's typed grammar edits onto `proposal.change_set` ops (the deltas/ vocabulary).

    Additive edits map directly; repair edits (narrow/retract) have no remove-op in the vocabulary, so
    they emit a rationale-bearing affix op flagged for manual handling rather than silently doing nothing.
    """
    pair = ticket.pair
    conf = max(ticket.confidence, 0.85)         # a human accepted it → high; routing-locked below
    prov = {"source": "deferral-ticket", "ticket": ticket.id, "hypothesis": hyp.id}
    ops: list[dict] = []

    def emit_edit(kind: str, params: dict) -> None:
        if kind in ("add_lexentry", "split_homograph"):
            form = params["form"]
            eid = _entry_id(pair, form)
            ops.append({"op": "lexical.entry.create", "lexeme_form": {pair: form}, "morph_type": "stem",
                        "entry": eid, "confidence": conf, "provenance": prov})
            if params.get("gloss") and params["gloss"] != "?":
                ops.append({"op": "lexical.sense.create", "entry": eid, "gloss": {"en": params["gloss"]},
                            "confidence": conf, "provenance": prov})
            if params.get("pos"):
                ops.append({"op": "lexical.entry.set_pos", "entry": eid, "pos": params["pos"],
                            "confidence": conf, "provenance": prov})
        elif kind == "add_allomorph":
            ops.append({"op": "lexical.entry.add_allomorph", "entry": _entry_id(pair, params["entry_form"]),
                        "form": params["allomorph"], "confidence": conf, "provenance": prov})
        elif kind == "add_affix":
            ops.append({"op": "morphophonology.affix.add", "form": params["form"],
                        "gram": params.get("gloss", params["form"]), "kind": params.get("kind", "suffix"),
                        "slot": params.get("slot_ord", 1), "confidence": conf, "provenance": prov})
        elif kind == "add_phon_rule":
            ops.append({"op": "morphophonology.rule.add", "name": params.get("id", "rule"),
                        "rule": params.get("archiphoneme", params.get("xml", "rule")),
                        "members": params.get("members", []), "confidence": conf, "provenance": prov})
        elif kind == "resegment":
            for sub in params.get("edits", []):
                emit_edit(sub["kind"], sub.get("params", {}))
        elif kind in ("narrow_affix", "retract_affix"):
            ops.append({"op": "morphophonology.affix.add", "form": params["form"],
                        "gram": params.get("gloss", params["form"]),
                        "rationale": f"REPAIR/{kind}: review manually (no remove-op in vocabulary)",
                        "confidence": conf, "provenance": prov})

    for e in hyp.edits:
        emit_edit(e.kind, e.params)

    # accept_with_words: the reviewer supplied extra surface forms → attach as allomorphs of the entry
    if extra_words:
        target_form = ticket.target.get("form", "")
        for w in extra_words:
            ops.append({"op": "lexical.entry.add_allomorph", "entry": _entry_id(pair, target_form),
                        "form": w, "confidence": conf, "provenance": prov})
    return ops


def _write_deltas(pair: str, ops: list[dict], *, accept_at: float = 0.85, delta_dir: Path | None = None) -> dict:
    """Append ops to the pair's delta store and lock them as accepted (a human decided)."""
    if not ops:
        return {"added": 0, "accepted": 0}
    store = DeltaStore.load((delta_dir or DELTA_STORE) / f"{pair}.deltas.jsonl")
    added = store.add(ops)
    store.route(accept_at=accept_at)
    for op in ops:                              # lock the human decision so routing won't undo it
        store.decide(op_signature(op), "accept", by="deferral-ticket")
    store.save()
    return {"added": added, "accepted": len(ops)}
