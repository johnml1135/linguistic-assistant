"""Accumulating driver — keep iterating the cycle until the grammar/lexicon stops growing.

Each round: run the cycle (resuming from the prior model, so roots/affixes/glosses/POS carry over and
extend into the next frequency tranche), then emit the round's deltas into the confidence-routed store.
**Loop-until-dry**: stop when N consecutive rounds add no new delta signatures (the grammar has
converged on the available evidence) — not a fixed count. This is the "go around and around finding
more words, adding senses, until everything frequent has a gloss + POS" loop.

Run: `python cycle/accumulate.py --pair spa --rounds 12 --seconds 120`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RESEARCH))

from induce.tdd import PAIR_DIR, run  # noqa: E402
from review.deltas.build_store import build as build_store  # noqa: E402

_OUT = Path(__file__).resolve().parent / "out"


def accumulate(pair: str, *, rounds: int = 12, seconds: float = 120.0, dry_after: int = 2,
               amb_cap: float = 5.0) -> dict:
    history: list[dict] = []
    dry = 0
    for i in range(1, rounds + 1):
        resume = i > 1 or (_OUT / f"{pair}_model.json").exists()
        print(f"\n===== {pair} round {i}/{rounds} (resume={resume}) =====")
        res = run(pair, seconds, amb_cap=amb_cap, resume=resume)
        store = build_store(pair, round_no=i)
        new = store["new_signatures"]
        dry = dry + 1 if new == 0 else 0
        row = {"round": i, "coverage": res["final_coverage"], "roots": res["lexicon"]["roots"],
               "affixes": len(res["affixes_kept"]), "new_deltas": new,
               "store_total": store["summary"]["total"], "route": store["route"]}
        history.append(row)
        print(f"[{pair}] round {i}: cov={row['coverage']} roots={row['roots']} affixes={row['affixes']} "
              f"new_deltas={new} store={row['store_total']} route={store['route']}")
        if dry >= dry_after:
            print(f"[{pair}] converged: {dry} consecutive rounds with no new deltas.")
            break
    return {"pair": pair, "rounds_run": len(history), "history": history,
            "final_store_total": history[-1]["store_total"] if history else 0}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=list(PAIR_DIR))
    ap.add_argument("--rounds", type=int, default=12)
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--dry-after", type=int, default=2, help="stop after this many no-new-delta rounds")
    ap.add_argument("--amb-cap", type=float, default=5.0)
    args = ap.parse_args(argv)
    s = accumulate(args.pair, rounds=args.rounds, seconds=args.seconds,
                   dry_after=args.dry_after, amb_cap=args.amb_cap)
    print(f"\n[{args.pair}] accumulate done: {s['rounds_run']} rounds, store now {s['final_store_total']} deltas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
