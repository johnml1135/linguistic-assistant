# benchmarks/linggym/

Replicates the [LingGym](https://github.com/changbingY/LingGym) multiple-choice
word-gloss inference benchmark against any harness endpoint — local models via
ik_llama.cpp, or Opus 4.8 as the ceiling.

How it matches the original:
- **Prompt** = the verbatim released item (the full **S+G+KP+T** condition; `prompt.py`
  can reconstruct lower levels for ablations).
- **Scoring** = generate, extract the A–D letter, exact-match (`scorer.py`). The released
  eval script generates with plain `model.generate(...)` (HF default **greedy**), so
  `--preset greedy` is the faithful, deterministic default. `--preset paper` matches the
  appendix's sampling (temp 0.7 / top-p 0.9 / repeat-penalty 1.1, seeded).
- **Data** = pinned via `fetch_data.py`. Verified: **19,612 items across 18 languages**
  (matches the paper). CC-BY-4.0 — attribute (Yang et al., EMNLP 2025).

## Files

| File | Role |
|---|---|
| `fetch_data.py` | Clone + pin the dataset into `.cache/` (gitignored). |
| `dataset.py` | Parse `*_questions.txt` blocks → `LingGymItem`. |
| `prompt.py` | Build the Figure-4 prompt at an info level (`full` = verbatim). |
| `scorer.py` | Extract the A–D letter (handles `<think>` blocks, "answer is C", bare `B`). |
| `presets.py` | `greedy` (default) / `paper` decoding. |
| `run.py` | CLI runner → per-item JSONL + `.summary.json` in `../results/`. |
| `sample/` | 6 vendored real items for offline smoke tests. |

## Run it

```bash
# 0. offline smoke test (no model) — should print accuracy ~0.25
python benchmarks/linggym/run.py --endpoint mock --limit 800 \
  --root benchmarks/linggym/.cache/LingGym/Benchmark_multiple_choice

# 1. get the data (once)
python benchmarks/linggym/fetch_data.py
```

On the 3090 box, build + serve a model, then run:

```powershell
# build ik_llama.cpp once
../serving/install-ik-llama.ps1

# --- Gemma 4 QAT ---
../serving/run-ik-llama-server.ps1 -Model D:\gguf\gemma-4-27b-it-qat-IQ4.gguf -CtxSize 4096
```
```bash
python benchmarks/linggym/run.py --endpoint ik_llama \
  --root benchmarks/linggym/.cache/LingGym/Benchmark_multiple_choice --limit 500
```
```powershell
# --- Qwen 3.6 (run non-thinking for the MC task; scorer also strips <think>) ---
../serving/run-ik-llama-server.ps1 -Model D:\gguf\qwen3.6-27b-instruct-Q5_K_M.gguf -CtxSize 4096
```
```bash
python benchmarks/linggym/run.py --endpoint ik_llama \
  --root benchmarks/linggym/.cache/LingGym/Benchmark_multiple_choice --limit 500

# frontier ceiling (needs ANTHROPIC_API_KEY)
python benchmarks/linggym/run.py --endpoint opus \
  --root benchmarks/linggym/.cache/LingGym/Benchmark_multiple_choice --limit 500
```

Run each model on the **same** `--limit` / item set to compare; drop `--limit` for the
full 19,612. Each run writes `../results/linggym_<endpoint>_<ts>.{jsonl,summary.json}`
(overall + per-language accuracy, unparsed count, tokens, latency).

## Caveats (carried from the design)

- **Contamination**: these are published-grammar items the models likely trained on, so
  scores **overstate** real-world capability. This run validates the harness and gives a
  paper-comparable number — the uncontaminated FLEx set (`../fieldwork/`) is the real signal.
- **Field labels** (to isolate the ~1,481 morphology+phonology items) are **not** in the
  released `*_questions.txt` files — they were chapter-level manual labels in the paper.
  TODO: pull them from the HuggingFace dataset (`cyang33/LingGym`) and add a `--field`
  filter. For now the runner reports overall + per-language.
- **Qwen 3.6 thinking**: serve/prompt it in non-thinking mode for fidelity; the scorer
  strips a leading `<think>…</think>` and takes the final letter as a safety net.
