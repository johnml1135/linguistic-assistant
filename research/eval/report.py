"""Write per-instance + summary results, mirroring research/benchmarks/results/ conventions."""

from __future__ import annotations

import json
from pathlib import Path


def summarize(records: list[dict]) -> dict:
    n = len(records)
    parsed = [r for r in records if r.get("parsed_ok")]
    rewards = [r.get("reward", 0.0) for r in records]
    return {
        "n": n,
        "n_parsed_ok": len(parsed),
        "parse_rate": round(len(parsed) / n, 4) if n else 0.0,
        "mean_reward": round(sum(rewards) / n, 4) if n else 0.0,
    }


def write_results(
    records: list[dict],
    *,
    out_dir: str | Path = "research/benchmarks/results",
    name: str = "eval_run",
    run_meta: dict | None = None,
) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jsonl_path = out / f"{name}.jsonl"
    summary_path = out / f"{name}.summary.json"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {**(run_meta or {}), **summarize(records)}
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return jsonl_path, summary_path
