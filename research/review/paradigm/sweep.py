"""Batch runner — sweep every language's UNLOCKED paradigms through the report pipeline, score against any
golden, and record onto the profiles. Turns the per-pair `run.py` into one system-wide snapshot: which
paradigms are locked (and why), which generated a report, which scored against a golden and how well.

This is the operational "how are we doing" and the data the Streamlit review UI reads.

    python -m review.paradigm.sweep [--endpoint heuristic|local|opus] [--no-gates] [--langs swh,tur]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review.paradigm import packet as PK          # noqa: E402
from review.paradigm import profiles as PF        # noqa: E402
from review.paradigm import run as R              # noqa: E402

LANGS = ["swh", "ind", "tgl", "spa", "tur", "vie", "hin", "rus"]


def switch_values(pair: str) -> dict:
    """The learned switch profile (gates the unlock). Falls back to empty (everything gated open) on error."""
    try:
        from review.deferrals.profile_detect import detect
        return {s.name: s.value for s in detect(pair)}
    except Exception:
        return {}


def sweep(langs: list[str] | None = None, *, endpoint: str | None = None, use_gates: bool = True) -> list[dict]:
    langs = langs or LANGS
    rows: list[dict] = []
    for L in langs:
        sw = switch_values(L) if use_gates else {}
        prof = PF.load(L)
        # mutating statuses: walk paradigms in priority (layer) order so learning one unlocks the next in
        # the SAME pass (the progressive cascade), and gate against the live statuses, not a one-shot set.
        statuses = {p["id"]: "learned" for p in prof["paradigms"] if p["paradigm_type"] == "switches"}
        for p in sorted(prof["paradigms"], key=lambda x: x.get("priority", 99)):
            ptype, pid = p["paradigm_type"], p["id"]
            if ptype == "switches":
                continue
            row = {"lang": L, "paradigm": ptype, "id": pid, "layer": p["layer"]}
            if use_gates and not PF.gate_ok(p.get("gate", ""), sw, statuses):
                row["state"] = "locked"
                row["gate"] = p.get("gate", "")
            elif not PK.has_builder(ptype):
                row["state"] = "no-builder"
            else:
                try:
                    out = R.run(L, ptype, endpoint=endpoint, record=True)
                    s = out.get("score")
                    detected = out["report"]["detected"]
                    row["state"] = "scored" if s else "generated"
                    row["detected"] = detected
                    if s:
                        row.update(overall=s["overall"], completeness=s["evidence_completeness"],
                                   faithfulness=s["faithfulness"])
                    statuses[pid] = "learned" if detected else "absent"   # cascade: unlock the next layer
                except Exception as e:  # noqa: BLE001
                    row["state"] = "error"
                    row["error"] = f"{type(e).__name__}: {e}"[:140]
            rows.append(row)
    return rows


def summarize(rows: list[dict]) -> dict:
    by_state: dict[str, int] = {}
    for r in rows:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    scored = [r for r in rows if r["state"] == "scored"]
    return {"n_paradigms": len(rows), "by_state": by_state, "n_scored": len(scored),
            "mean_overall": round(sum(r["overall"] for r in scored) / len(scored), 3) if scored else None}


def _print_table(rows: list[dict]) -> None:
    print(f"{'lang':4} {'paradigm':14} {'layer':10} {'state':10} {'over':>5} {'comp':>5} {'faith':>5}")
    for r in rows:
        sc = (f"{r.get('overall',''):>5} {r.get('completeness',''):>5} {r.get('faithfulness',''):>5}"
              if r["state"] == "scored" else "")
        extra = r.get("gate", "") if r["state"] == "locked" else r.get("error", "")
        print(f"{r['lang']:4} {r['paradigm']:14} {r['layer']:10} {r['state']:10} {sc}  {extra}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--endpoint", default="heuristic")
    ap.add_argument("--no-gates", action="store_true", help="run every paradigm, ignore the progressive gate")
    ap.add_argument("--langs", default="", help="comma list (default all 8)")
    ap.add_argument("--out", default="", help="write sweep rows + summary to this JSON path")
    args = ap.parse_args(argv)
    langs = [x.strip() for x in args.langs.split(",") if x.strip()] or None
    rows = sweep(langs, endpoint=(None if args.endpoint == "heuristic" else args.endpoint),
                 use_gates=not args.no_gates)
    _print_table(rows)
    summ = summarize(rows)
    print("\nSUMMARY:", json.dumps(summ, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps({"rows": rows, "summary": summ}, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
