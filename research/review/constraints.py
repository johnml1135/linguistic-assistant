"""Constraint induction — the first-class loop that turns enumerated allomorphs / homographic morphemes
into environment-conditioned constraints, with the right roles in the right places:

    witness   THOT          supplies co-occurrence counts (dossier.py)            — dumb, never judges
    generator LLM           proposes encodable environments (generate_constraint) — the intelligence
    judge     re-parse + IG re-aligns under each environment, scores by info-gain — deterministic verdict
              (judge.py)    + constrainedness; ΔMDL / non-regression gate

Flow:  prepare (dossier)  →  candidate environments (seed + LLM)  →  SCREEN on the conflated alignment
       →  for the winner, CONFIRM by re-aligning under the split (realign_with_env)  →  route:
          accept → a constraint delta (the env + the per-bucket sense — the meaningful `u1…u5`);
          no gain → a deferral ticket for a speaker.

SCOPE: this is the HOMOGRAPH judge — one surface morpheme, several senses that align to DIFFERENT English
words (the user's `u → 5 senses` case). It is NOT the allomorphy judge: allomorphs (meN→mem/men,
decir→dij/dic) share ONE English correspondence, so alignment information-gain is ≈0 by construction.
Allomorphy is collapsed by the MDL + HC-round-trip gate in `promote.py` / the phonology consolidation —
a different metric. Keep them separate.

CLI:  uv run python -m review.constraints --pair swh --morpheme ku --kind prefix [--llm] [--max-env N]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review import dossier as D       # noqa: E402
from review import judge as J         # noqa: E402

SKILL = _RESEARCH / "skills" / "generate_constraint.md"


# ── the generator (gated: no LLM → seed environments only) ──────────────────────────────────────────────
def llm_environments(dossier: dict, *, endpoint: str = "local") -> list[dict]:
    """Ask the LLM (via the harness) to propose environments for this morpheme. Returns [] if no endpoint
    is reachable — the loop then runs on the deterministic seed environments alone (audio-style: optional,
    additive). Never raises into the caller."""
    try:
        from propose.harness.base import Message
        from propose.harness.registry import build_client
        client = build_client(endpoint)
        sys_prompt = SKILL.read_text(encoding="utf-8")
        msg = [Message(role="system", content=sys_prompt),
               Message(role="user", content=json.dumps(dossier, ensure_ascii=False))]
        res = client.complete(msg, max_tokens=2048)
        data = json.loads(res.text)
        if not data.get("is_ambiguous", True):
            return []
        return [e for e in data.get("environments", []) if e.get("kind")]
    except Exception as exc:        # offline / no server / bad JSON — degrade to seeds, loudly in summary
        return [{"_llm_error": str(exc)[:120]}] if False else []


def _specs(dossier: dict, use_llm: bool) -> list[dict]:
    specs = list(dossier.get("seed_environments", []))
    if use_llm:
        specs = llm_environments(dossier) + specs        # LLM first (richer/tighter), seeds as fallback
    # de-dup by (kind, set/value)
    seen, out = set(), []
    for s in specs:
        key = (s.get("kind"), tuple(sorted(s.get("set", []))) or s.get("value"))
        if key not in seen:
            seen.add(key); out.append(s)
    return out


def run(pair: str, morpheme: str, kind: str = "prefix", *, use_llm: bool = False, sample: int = 0,
        min_gain: float = 0.15, max_env: int = 10) -> dict:
    """End-to-end for one morpheme. Each candidate environment is APPLIED (split + THOT re-align) and
    scored by distribution information-gain — the honest signal (the conflated per-occurrence screen could
    not detect splits). Returns a decision record (also the unit the web UI / deltas consume)."""
    ctx = D.prepare(pair, morpheme, kind, sample=sample)
    dossier = ctx["dossier"]
    specs = _specs(dossier, use_llm)[:max_env]

    results = []
    for s in specs:
        try:
            r = D.realign_distributions(ctx, s)
        except ValueError:
            continue
        if r["n_in"] == 0 or r["n_out"] == 0:            # env doesn't partition — skip
            continue
        r["info_gain"] = J.information_gain_dist(r["dist_in"], r["dist_out"], r["n_in"], r["n_out"])
        results.append(r)

    verdict = J.decide_dist(results, min_gain=min_gain)
    decision = verdict["decision"]
    best = next((r for r in results if r["label"] == verdict["best"]), None)
    return {
        "pair": pair, "morpheme": morpheme, "kind": kind, "n_occ": dossier["n_occ"],
        "conflated_distribution": dossier["conflated_distribution"],
        "decision": decision, "best_environment": verdict["best"],
        "info_gain": verdict["best_gain"], "coverage": verdict["best_coverage"],
        "best_sense_in": (best["dist_in"] if best else {}),
        "best_sense_out": (best["dist_out"] if best else {}),
        "winning_spec": verdict.get("best_spec"), "n_genuine": verdict["n_genuine"],
        "n_artifacts": verdict["n_artifacts"],
        "all_environments": [{"label": r["label"], "info_gain": r["info_gain"], "coverage": r["coverage"],
                              "n_in": r["n_in"], "n_out": r["n_out"], "artifact": J.is_artifact(r),
                              "n_hosts_in": r.get("n_hosts_in"), "top_host_share_in": r.get("top_host_share_in"),
                              "top_in": sorted(r["dist_in"].items(), key=lambda x: -x[1])[:4],
                              "top_out": sorted(r["dist_out"].items(), key=lambda x: -x[1])[:4]}
                             for r in sorted(results, key=lambda r: -r["info_gain"])],
        "route": "constraint-delta" if decision == "accept" else "deferral-ticket",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Induce an environment/constraint for one morpheme.")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--morpheme", required=True)
    ap.add_argument("--kind", default="prefix", choices=["prefix", "suffix"])
    ap.add_argument("--llm", action="store_true", help="ask the LLM for environments (else seeds only)")
    ap.add_argument("--sample", type=int, default=0, help="cap verses (0 = all)")
    ap.add_argument("--min-gain", type=float, default=0.15)
    ap.add_argument("--max-env", type=int, default=10, help="cap candidate environments (each = 1 re-align)")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rec = run(a.pair, a.morpheme, a.kind, use_llm=a.llm, sample=a.sample, min_gain=a.min_gain,
              max_env=a.max_env)
    print(f"\n{rec['pair']} '{rec['morpheme']}' ({rec['kind']})  n_occ={rec['n_occ']}")
    print(f"conflated: {rec['conflated_distribution']}")
    print(f"DECISION: {rec['decision'].upper()}  best={rec['best_environment']!r}  "
          f"IG={rec['info_gain']}  coverage={rec['coverage']}  -> {rec['route']}")
    print(f"  ({rec['n_genuine']} genuine split(s), {rec['n_artifacts']} host-translation artifact(s) discarded)\n")
    print("environments (realigned, by info-gain):")
    for e in rec["all_environments"]:
        tag = "  [ARTIFACT: one host stem]" if e["artifact"] else ""
        print(f"  IG={e['info_gain']:+.3f} cov={e['coverage']:.2f} ({e['n_in']}/{e['n_in']+e['n_out']}) "
              f"hosts_in={e['n_hosts_in']} top_host={e['top_host_share_in']}  {e['label']}{tag}")
        print(f"       in : {e['top_in']}")
        print(f"       out: {e['top_out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
