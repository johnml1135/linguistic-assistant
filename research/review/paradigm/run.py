"""Run the paradigm-report loop for one (language, paradigm) and score it against the golden.

    python -m review.paradigm.run --pair swh --paradigm noun-class [--endpoint heuristic|gemma|opus]

Prints the evidence packet audit, the generated report, and the three scores (overall /
evidence_completeness / faithfulness) with the per-cell breakdown so you can see what the DETECTOR missed
vs what the GENERATOR mangled.
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
from review.paradigm import report as RP          # noqa: E402
from review.paradigm import score as SC           # noqa: E402
from review.paradigm.schema import ParadigmReport, golden_path  # noqa: E402


def run(pair: str, paradigm: str, endpoint: str | None = None, show_packet: bool = False,
        record: bool = True) -> dict:
    pkt = PK.assemble(pair, paradigm)
    violations = PK.audit(pkt)
    rep = RP.generate(pkt, endpoint=endpoint)
    out = {"pair": pair, "paradigm": paradigm, "endpoint": endpoint or "heuristic",
           "audit_violations": violations, "report": rep.to_dict()}
    gp = golden_path(pair, paradigm)
    if gp.exists():
        golden = ParadigmReport.load(gp)
        out["score"] = SC.score(rep, golden, pkt)
    else:
        out["score"] = None
        out["note"] = f"no golden at {gp}"
    # record the result onto the live, queryable per-language profile (report metric -> profile state)
    if record:
        para = PF.find_by_type(pair, paradigm)
        if para:
            status = "absent" if not rep.detected else ("learned" if out["score"] else "candidate")
            metric = dict(out["score"], as_of="run", endpoint=out["endpoint"]) if out["score"] else None
            PF.record_result(pair, para["id"], status=status, metric=metric)
            out["profile_id"] = para["id"]
    if show_packet:
        out["packet"] = pkt
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--paradigm", required=True)
    ap.add_argument("--endpoint", default=None)
    ap.add_argument("--show-packet", action="store_true")
    args = ap.parse_args(argv)
    out = run(args.pair, args.paradigm, endpoint=args.endpoint, show_packet=args.show_packet)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
