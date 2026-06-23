"""Run the LingGym multiple-choice benchmark against any harness endpoint.

Examples
--------
    # offline pipeline test (no model)
    python benchmarks/linggym/run.py --endpoint mock --root benchmarks/linggym/sample

    # local model via ik_llama.cpp (start serving/run-ik-llama-server.ps1 first)
    python benchmarks/linggym/run.py --endpoint ik_llama \
        --root benchmarks/linggym/.cache/LingGym/Benchmark_multiple_choice --limit 200

    # frontier ceiling
    python benchmarks/linggym/run.py --endpoint opus \
        --root benchmarks/linggym/.cache/LingGym/Benchmark_multiple_choice --limit 200
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

# Make `harness` and `benchmarks` importable when run as a script.
RESEARCH_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RESEARCH_ROOT))

from propose.harness import Message, build_client  # noqa: E402
from propose.harness.config import DEFAULT_ENDPOINTS  # noqa: E402
from eval.benchmarks.linggym import dataset, prompt as promptlib, scorer  # noqa: E402
from eval.benchmarks.linggym.presets import PRESETS  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parent / "sample"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", default="mock", help="harness endpoint (mock, ik_llama, vllm, opus)")
    ap.add_argument("--model", default=None, help="override the endpoint's model")
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="dir of *_questions.txt files")
    ap.add_argument("--languages", default=None, help="comma-separated language filter")
    ap.add_argument("--limit", type=int, default=None, help="cap number of items (first-N in file order)")
    ap.add_argument("--sample", type=int, default=None, help="random sample N across the FULL dataset (representative across languages)")
    ap.add_argument("--sample-seed", type=int, default=0, help="seed for --sample (same seed => same items)")
    ap.add_argument("--level", default="full", choices=list(promptlib.LEVELS), help="info level")
    ap.add_argument("--preset", default="greedy", choices=list(PRESETS), help="decoding preset")
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--prompt-suffix", default="", help="appended to every prompt (e.g. '/no_think' for Qwen)")
    ap.add_argument("--out", default=None, help="results JSONL path (default: results/linggym_<endpoint>_<ts>.jsonl)")
    args = ap.parse_args()

    languages = set(args.languages.split(",")) if args.languages else None
    items = dataset.load_items(args.root, languages=languages, limit=None if args.sample else args.limit)
    if not items:
        print(f"No items found under {args.root!r}", file=sys.stderr)
        return 2
    if args.sample and args.sample < len(items):
        import random
        items = random.Random(args.sample_seed).sample(items, args.sample)
        items.sort(key=lambda it: it.qid)  # stable run order

    overrides = {"model": args.model} if args.model else {}
    client = build_client(args.endpoint, **overrides)

    # Decoding params apply only to sampling-capable (openai_compat) endpoints; the
    # Anthropic endpoint rejects them, so drop them there.
    kind = DEFAULT_ENDPOINTS[args.endpoint].kind if args.endpoint in DEFAULT_ENDPOINTS else "openai_compat"
    decoding = dict(PRESETS[args.preset]) if kind == "openai_compat" else {}

    ts = time.strftime("%Y%m%d-%H%M%S")
    out_path = Path(args.out) if args.out else RESEARCH_ROOT / "benchmarks" / "results" / f"linggym_{args.endpoint}_{ts}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = correct = unparsed = 0
    by_lang: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # lang -> [correct, total]
    t0 = time.perf_counter()

    with out_path.open("w", encoding="utf-8") as fh:
        for it in items:
            text = promptlib.build_prompt(it, level=args.level)
            if args.prompt_suffix:
                text = text + "\n" + args.prompt_suffix
            res = client.complete([Message("user", text)], max_tokens=args.max_tokens, **decoding)
            pred = scorer.extract_letter(res.text)
            ok = scorer.score(pred, it.gold)
            n += 1
            correct += int(ok)
            unparsed += int(pred is None)
            by_lang[it.language][0] += int(ok)
            by_lang[it.language][1] += 1
            fh.write(json.dumps({
                "qid": it.qid, "language": it.language, "level": args.level,
                "gold": it.gold, "pred": pred, "correct": ok,
                "raw": res.text, "input_tokens": res.input_tokens,
                "output_tokens": res.output_tokens, "latency_s": res.latency_s,
            }, ensure_ascii=False) + "\n")
            if n % 50 == 0:
                print(f"  {n}/{len(items)}  acc={correct/n:.3f}", file=sys.stderr)

    elapsed = time.perf_counter() - t0
    summary = {
        "endpoint": args.endpoint, "model": getattr(client, "name", args.endpoint),
        "level": args.level, "preset": args.preset, "max_tokens": args.max_tokens,
        "sample": args.sample, "sample_seed": args.sample_seed,
        "n": n, "correct": correct, "accuracy": correct / n,
        "unparsed": unparsed, "elapsed_s": round(elapsed, 1),
        "by_language": {k: {"correct": v[0], "total": v[1], "accuracy": v[0] / v[1]}
                        for k, v in sorted(by_lang.items())},
        "results_file": str(out_path),
    }
    summary_path = out_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== LingGym [{args.endpoint} / {args.level} / {args.preset}] ===")
    print(f"items={n}  accuracy={correct / n:.4f}  unparsed={unparsed}  elapsed={elapsed:.1f}s")
    print(f"per-item: {out_path}")
    print(f"summary:  {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
