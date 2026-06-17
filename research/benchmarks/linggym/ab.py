"""A/B test the 5 research-backed harness improvements on LingGym (see harness_research.md).

One ARM per invocation (so each fits a time budget). Talks directly to the ik_llama
OpenAI-compatible endpoint for fine control over logprobs / permutation.

Arms:
  baseline  - generate + parse letter (current harness behavior)
  logprob   - first-token logprob argmax over A-D (no parsing)
  prior     - logprob + per-letter prior debiasing (PriDe-style)
  permute   - cyclic option-permutation (x4) + majority vote (on generation)
  fewshot   - baseline + 3 held-out exemplars prepended
  skill     - baseline + system prompt (skills/gloss_reference.md)

Example:
  python benchmarks/linggym/ab.py --arm logprob --label gemma31b \
    --root benchmarks/linggym/.cache/LingGym/Benchmark_multiple_choice --sample 200 --sample-seed 13
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

RESEARCH_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RESEARCH_ROOT))
from benchmarks.linggym import dataset, scorer  # noqa: E402

ENDPOINT = "http://localhost:8080/v1/chat/completions"
LETTERS = ["A", "B", "C", "D"]
SKILL = (RESEARCH_ROOT / "skills" / "gloss_reference.md").read_text(encoding="utf-8")
_HTTP = httpx.Client(timeout=120.0)


def chat(messages, max_tokens=8, logprobs=False, top_logprobs=0):
    payload = {"model": "local", "temperature": 0, "max_tokens": max_tokens, "messages": messages}
    if logprobs:
        payload["logprobs"] = True
        payload["top_logprobs"] = top_logprobs
    r = _HTTP.post(ENDPOINT, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]


def gen_letter(prompt, system=None):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    return scorer.extract_letter(chat(msgs, max_tokens=8)["message"]["content"])


def letter_logprobs(prompt, system=None):
    """Return {A,B,C,D: logprob} from the first generated token."""
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    ch = chat(msgs, max_tokens=1, logprobs=True, top_logprobs=20)
    out = {L: -100.0 for L in LETTERS}
    content = (ch.get("logprobs") or {}).get("content") or []
    if content:
        for t in content[0].get("top_logprobs", []):
            tok = t["token"].strip().upper()
            if tok in out:
                out[tok] = max(out[tok], t["logprob"])
    return out


def rotate_options(item, r):
    """Splice the option block of prompt_full into cyclic rotation r.
    Returns (prompt, displayed_letter -> gold?) mapping via original letters."""
    lines = item.prompt_full.splitlines()
    contents = [re.sub(r"^[A-D]:\s*", "", l) for l in lines[5:9]]  # strip 'A:' etc.
    disp_lines, disp_to_orig = [], {}
    for i, disp in enumerate(LETTERS):
        oi = (i + r) % 4
        disp_lines.append(f"{disp}: {contents[oi]}")
        disp_to_orig[disp] = LETTERS[oi]
    prompt = "\n".join(lines[:5] + disp_lines + lines[9:])
    return prompt, disp_to_orig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True,
                    choices=["baseline", "logprob", "prior", "permute", "fewshot", "skill"])
    ap.add_argument("--label", required=True, help="model label for output filenames")
    ap.add_argument("--root", required=True)
    ap.add_argument("--sample", type=int, default=200)
    ap.add_argument("--sample-seed", type=int, default=13)
    ap.add_argument("--prior-n", type=int, default=40, help="held-out items to estimate the letter prior")
    ap.add_argument("--fewshot-k", type=int, default=3)
    args = ap.parse_args()

    allitems = dataset.load_items(args.root)
    rng = random.Random(args.sample_seed)
    sample = rng.sample(allitems, args.sample)
    sample_ids = {it.qid for it in sample}
    pool = [it for it in allitems if it.qid not in sample_ids]  # held-out (fewshot/prior)

    # Prior estimation (PriDe): displayed-letter frequency over cyclic perms of held-out items.
    prior_log = {L: 0.0 for L in LETTERS}
    if args.arm == "prior":
        cnt = Counter()
        for it in pool[:args.prior_n]:
            for r in range(4):
                p, _ = rotate_options(it, r)
                lp = letter_logprobs(p)
                cnt[max(lp, key=lp.get)] += 1
        tot = sum(cnt.values()) or 1
        import math
        prior_log = {L: math.log((cnt[L] + 1) / (tot + 4)) for L in LETTERS}

    fewshot_prefix = ""
    if args.arm == "fewshot":
        exs = pool[:args.fewshot_k]
        blocks = [f"{e.prompt_full}\nCorrect Answer: {e.gold}" for e in exs]
        fewshot_prefix = "Here are solved examples:\n\n" + "\n\n".join(blocks) + "\n\nNow answer this one:\n"

    n = correct = unparsed = 0
    t0 = time.perf_counter()
    out = RESEARCH_ROOT / "benchmarks" / "results" / f"ab_{args.label}_{args.arm}.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for it in sample:
          try:
            if args.arm == "baseline":
                pred = gen_letter(it.prompt_full)
            elif args.arm == "skill":
                pred = gen_letter(it.prompt_full, system=SKILL)
            elif args.arm == "fewshot":
                pred = gen_letter(fewshot_prefix + it.prompt_full)
            elif args.arm == "logprob":
                lp = letter_logprobs(it.prompt_full)
                pred = max(lp, key=lp.get)
            elif args.arm == "prior":
                lp = letter_logprobs(it.prompt_full)
                pred = max(LETTERS, key=lambda L: lp[L] - prior_log[L])
            elif args.arm == "permute":
                votes = Counter()
                for r in range(4):
                    p, d2o = rotate_options(it, r)
                    dl = gen_letter(p)
                    if dl in d2o:
                        votes[d2o[dl]] += 1
                pred = votes.most_common(1)[0][0] if votes else None
          except Exception as e:
            pred = None
            print(f"  ! {it.qid}: {type(e).__name__}", file=sys.stderr)
          ok = scorer.score(pred, it.gold)
          n += 1; correct += int(ok); unparsed += int(pred is None)
          fh.write(json.dumps({"qid": it.qid, "gold": it.gold, "pred": pred, "correct": ok}) + "\n")

    elapsed = time.perf_counter() - t0
    summary = {"arm": args.arm, "label": args.label, "n": n, "correct": correct,
               "accuracy": correct / n, "unparsed": unparsed, "elapsed_s": round(elapsed, 1),
               "sample_seed": args.sample_seed}
    out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[{args.label}/{args.arm}] acc={correct/n:.4f} n={n} unparsed={unparsed} elapsed={elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
