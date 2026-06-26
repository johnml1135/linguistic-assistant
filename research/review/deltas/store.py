"""Accumulating, git-trackable delta store with confidence routing — the controllable backend.

The cycle/LLM emit **change-set ops** (the `proposal.change_set` vocabulary: `lexical.*` MiniLcm-shaped,
`morphophonology.*` HC, `bilingual.*`). This store is where they land and accumulate across many runs:

  * **append-only + idempotent** — ops are merged by `op_signature` (op type + key), so running the cycle
    a dozen times reinforces existing entries (confidence ↑, `rounds_seen` ↑) instead of duplicating.
  * **confidence routing** — each op is routed by score into a status: `accepted` (high → auto-apply),
    `review` (medium → human or LLM second-guess), `deferred` (low). A human/LLM `decision`
    (`accept`/`reject`) is **locked** and never auto-rerouted.
  * **diffs, not DB writes** — the store is a plain JSONL file you commit; appliers (MiniLcm/Harmony,
    FLExTools/flexlibs) consume the `accepted` set. The store never touches FieldWorks itself.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_RESEARCH))

from propose.change_set import op_signature, validate_change_set  # noqa: E402
from propose.contract import ChangeSet  # noqa: E402

# default routing thresholds (tunable per project)
ACCEPT_AT = 0.85
REVIEW_AT = 0.5

# THE canonical delta-store directory — one source of truth. (Historically some callers hardcoded the
# repo-root `deltas/store/`, which diverged from where build_store writes and left readers on a stale
# stub; everyone now resolves the path through store_path().)
STORE_DIR = Path(__file__).resolve().parent / "store"


def store_path(pair: str) -> Path:
    return STORE_DIR / f"{pair}.deltas.jsonl"


@dataclass
class RouteResult:
    accepted: int = 0
    review: int = 0
    deferred: int = 0
    locked: int = 0


@dataclass
class DeltaStore:
    """An accumulating set of change-set ops keyed by signature, persisted as JSONL."""

    path: Path
    by_sig: dict[tuple[str, str], dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "DeltaStore":
        p = Path(path)
        store = cls(path=p)
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    store.by_sig[op_signature(rec)] = rec
        return store

    def add(self, ops: list[dict]) -> int:
        """Merge ops in (idempotent by signature). Returns the count of NEW signatures added.

        On a repeat signature: keep the max confidence seen, bump `rounds_seen`, and append provenance —
        so reinforcement across runs is recorded. A locked (human/LLM-decided) record is never overwritten
        except to bump `rounds_seen`.
        """
        new = 0
        for op in ops:
            sig = op_signature(op)
            prior = self.by_sig.get(sig)
            if prior is None:
                rec = dict(op)
                rec["rounds_seen"] = 1
                rec.setdefault("status", "deferred")
                rec["provenance"] = [op.get("provenance")] if op.get("provenance") else []
                self.by_sig[sig] = rec
                new += 1
            else:
                prior["rounds_seen"] = prior.get("rounds_seen", 1) + 1
                if not prior.get("locked"):
                    prior["confidence"] = max(prior.get("confidence", 0.0) or 0.0, op.get("confidence", 0.0) or 0.0)
                    for f in ("gloss", "pos", "gram", "rationale"):  # fill any field a later, better op carries
                        if op.get(f) and not prior.get(f):
                            prior[f] = op[f]
                if op.get("provenance"):
                    prior.setdefault("provenance", []).append(op["provenance"])
        return new

    def decide(self, signature: tuple[str, str], decision: str, by: str = "human") -> bool:
        """Lock a human/LLM decision (`accept`|`reject`) so routing won't override it."""
        rec = self.by_sig.get(signature)
        if rec is None:
            return False
        rec["status"] = "accepted" if decision == "accept" else "rejected"
        rec["locked"] = True
        rec["decided_by"] = by
        return True

    def route(self, accept_at: float = ACCEPT_AT, review_at: float = REVIEW_AT) -> RouteResult:
        """Assign a status to every non-locked op from its confidence. Returns the tally."""
        r = RouteResult()
        for rec in self.by_sig.values():
            if rec.get("locked"):
                r.locked += 1
                continue
            c = rec.get("confidence", 0.0) or 0.0
            rec["status"] = "accepted" if c >= accept_at else "review" if c >= review_at else "deferred"
            setattr(r, rec["status"], getattr(r, rec["status"]) + 1)
        return r

    def by_status(self, status: str) -> list[dict]:
        return sorted((r for r in self.by_sig.values() if r.get("status") == status),
                      key=lambda r: -(r.get("confidence", 0.0) or 0.0))

    def accepted_change_set(self) -> ChangeSet:
        """The accepted (or locked-accept) ops as a validated ChangeSet — the appliers' input."""
        ops = [{k: v for k, v in r.items() if k not in ("status", "rounds_seen", "locked", "decided_by")}
               for r in self.by_sig.values() if r.get("status") == "accepted"]
        cs = validate_change_set(json.dumps({"ops": ops}))
        if not isinstance(cs, ChangeSet):  # pragma: no cover — emit must produce valid ops
            raise ValueError(f"accepted ops failed validation: {cs}")
        return cs

    def save(self) -> None:
        recs = sorted(self.by_sig.values(), key=lambda r: (r.get("op", ""), str(op_signature(r)[1])))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")

    def summary(self) -> dict:
        from collections import Counter
        by_status = Counter(r.get("status", "?") for r in self.by_sig.values())
        by_optype = Counter(str(r.get("op", "?")).split(".")[0] for r in self.by_sig.values())
        return {"total": len(self.by_sig), "by_status": dict(by_status), "by_tier": dict(by_optype)}
