"""Accumulate a cycle run's deltas into the per-language store and route by confidence.

Run after each cycle round (and `llm_propose`): `python deltas/build_store.py --pair spa --round 3`.
Re-running is safe and additive — signatures merge, `rounds_seen` climbs, confidence takes the max.
The store is a committable JSONL under `deltas/store/`; appliers consume its `accepted` ops.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_RESEARCH))

from review.deltas.emit import PAIR_DIR, emit_ops  # noqa: E402
from review.deltas.store import ACCEPT_AT, REVIEW_AT, DeltaStore  # noqa: E402

STORE_DIR = Path(__file__).resolve().parent / "store"


def build(pair: str, *, round_no: int = 1, accept_at: float = ACCEPT_AT, review_at: float = REVIEW_AT) -> dict:
    store = DeltaStore.load(STORE_DIR / f"{pair}.deltas.jsonl")
    ops = emit_ops(pair, round_no=round_no)
    new = store.add(ops)
    route = store.route(accept_at, review_at)
    store.save()
    return {"pair": pair, "emitted": len(ops), "new_signatures": new,
            "route": asdict(route), "summary": store.summary(), "store": str(store.path)}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--round", type=int, default=1, dest="round_no")
    ap.add_argument("--accept-at", type=float, default=ACCEPT_AT)
    ap.add_argument("--review-at", type=float, default=REVIEW_AT)
    args = ap.parse_args(argv)
    s = build(args.pair, round_no=args.round_no, accept_at=args.accept_at, review_at=args.review_at)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
