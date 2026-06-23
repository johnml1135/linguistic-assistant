"""CLI: run the eval/proposal loop against the golden set (or the offline fixture).

Examples
--------
    # offline smoke test — no model, no network, no golden data needed
    python research/eval/run.py --fixture

    # local 30B (start serving/run-ik-llama-server.ps1 first), real golden languages
    python research/eval/run.py --endpoint ik_llama --glottocodes lezg1247,tsez1242 --tier hard

    # BYOK frontier arm over the same instances
    python research/eval/run.py --endpoint opus --glottocodes lezg1247,tsez1242 --tier hard
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make research/ importable (harness, proposal, eval) regardless of CWD.
_RESEARCH_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RESEARCH_DIR))

from eval.report import write_results  # noqa: E402
from eval.runner import run_instances  # noqa: E402
from eval.stub_scorer import StubScorer  # noqa: E402
from propose.propose import ProposeConfig  # noqa: E402


def _load_golden_scorer():
    """Adapt to the sibling agent's concrete scorer when present; else fall back to the stub."""
    try:  # name TBD — reconcile in tasks 5.2 / 6.4
        from engine.scorer import build_scorer  # type: ignore

        return build_scorer()
    except Exception:
        print("[run] golden scorer not importable yet — using StubScorer (pipeline test only).")
        return StubScorer()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixture", action="store_true", help="offline mock+fixture+stub run (no model/network)")
    ap.add_argument("--endpoint", default="ik_llama", help="registered endpoint (ik_llama|opus|vllm|ollama|mock)")
    ap.add_argument("--glottocodes", default="", help="comma-separated glottocodes under research/golden/")
    ap.add_argument("--tier", default="hard", help="difficulty tier")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--no-grammar", action="store_true", help="disable GBNF constraint (use json_schema)")
    ap.add_argument("--out", default="research/benchmarks/results")
    ap.add_argument("--name", default=None, help="output basename (default derived from endpoint)")
    args = ap.parse_args()

    if args.fixture:
        from eval.fixtures import MockProposer, fixture_instances

        instances = fixture_instances()
        client = MockProposer()
        scorer = StubScorer()
        backend_kind = "mock"
        name = args.name or "eval_fixture"
    else:
        from propose.harness.config import DEFAULT_ENDPOINTS
        from propose.harness.registry import build_client

        from eval.instances import load_golden_instances

        glottocodes = [g.strip() for g in args.glottocodes.split(",") if g.strip()]
        if not glottocodes:
            ap.error("--glottocodes is required unless --fixture is given")
        instances = load_golden_instances(glottocodes, tier=args.tier)
        if not instances:
            print("[run] no instances loaded — check research/golden/ and glottocodes.")
            return 1
        client = build_client(args.endpoint)
        backend_kind = DEFAULT_ENDPOINTS[args.endpoint].kind
        scorer = _load_golden_scorer()
        name = args.name or f"eval_{args.endpoint}_{args.tier}"

    cfg = ProposeConfig(backend_kind=backend_kind, seed=args.seed, use_grammar=not args.no_grammar)
    records = run_instances(instances, client, scorer, cfg)
    run_meta = {
        "endpoint": "fixture/mock" if args.fixture else args.endpoint,
        "backend_kind": backend_kind,
        "seed": args.seed,
        "tier": args.tier,
        "scorer": getattr(scorer, "name", "?"),
        "use_grammar": not args.no_grammar,
    }
    jsonl_path, summary_path = write_results(records, out_dir=args.out, name=name, run_meta=run_meta)

    n = len(records)
    mean = sum(r.get("reward", 0.0) for r in records) / n if n else 0.0
    parsed = sum(1 for r in records if r.get("parsed_ok"))
    print(f"\n{name}: n={n}  parse_ok={parsed}/{n}  mean_reward={mean:.4f}")
    print(f"  per-instance: {jsonl_path}")
    print(f"  summary:      {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
