# research/

The research backbone for the linguistic-assistant project: a **provider-agnostic
LLM harness** and a **benchmark** that scores `(model × quantization × harness-config)`
on the linguistic tasks this project actually cares about — **word-level morphology
and phonology**, not syntax.

This is the core research that justifies the product: it tells us *which* model, *at
which quantization*, *behind which harness*, is worth shipping — for both the
**BYOK/frontier** path and the **offline local** path (a single RTX 3090 running
Gemma 4 / Qwen 3.6).

> Status: **scaffold + thin-harness skeleton.** The harness runs against any
> OpenAI-compatible endpoint (Ollama / llama.cpp / vLLM) and against Claude Opus 4.8.
> Benchmarks and data pipelines are specified here and stubbed; not yet implemented.

---

## Why this exists (and what we learned)

The differentiator for this whole project is the **AI judgment / skills layer**, which
wants a frontier model. But a large share of users are **offline for weeks**, and the
local models that *can* run offline are weakest at exactly morphology/agreement
reasoning. The only way to make a defensible call about what to ship — frontier-BYOK,
SIL-hosted, or local — is to **measure** the intelligence ↔ cost ↔ offline-feasibility
frontier on our own tasks. That measurement is this folder.

### What LingGym is, and the three catches

[LingGym](https://github.com/changbingY/LingGym) (EMNLP 2025, CC-BY-4.0, runnable
Python eval) is a **multiple-choice word-gloss inference** benchmark over interlinear
glossed text from 18 reference grammars. It's directly usable and tests the exact model
families we care about — but three properties shape how we use it:

1. **Distribution is ~the inverse of our scope.** LingGym is **85% syntax, 7%
   morphology, 0.36% phonology**. We are word-parsing only. So LingGym is a
   **calibration baseline + wiring smoke-test**, *not* the primary benchmark. The
   primary benchmark is morphology/phonology built from real FLEx data.
2. **It is contaminated.** Sentence-only accuracy sits well above the random floor →
   models trained on these published grammars. On a real low-resource language there is
   no such contamination, so LingGym scores **overstate** real-world capability.
3. **It is discriminative (MC); our product is generative.** LingGym measures "pick the
   right gloss from 4." The product *produces* segmentations and *proposes* rules, then
   HermitCrab round-trips them. The paper found **CoT barely helps** on the MC task — a
   warning that harness/prompt optimization pays off on the **generative, tool-using**
   task, not on MC. Measure harness design on the generative task.

We **bootstrap** the fieldwork benchmark from LingGym's ~1,481 morphology+phonology
items (uncontaminated FLEx-derived data comes next; see `data_prep/`).

---

## Layout

```
research/
  harness/        # thin provider-agnostic LLM client — one interface, swap endpoints
  skills/         # portable skill assets: markdown prompts + JSON tool/output contracts
  benchmarks/
    linggym/      # external calibration — MC, contaminated, mostly syntax
    fieldwork/    # PRIMARY — morphology/phonology; discriminative + generative modes
    results/      # committed Parquet/CSV + generated reports
  data_prep/      # flexlibs + FlexToolsMCP extraction (Windows-only, ONE-TIME) → portable JSON
  data_gen/       # Opus 4.8 batch jobs: synthetic items, preference/RL pairs, LLM-as-judge
  models/         # Gemma 4 / Qwen 3.6 configs, quant variants, VRAM notes, launch scripts
  scripts/        # smoke_test.py and other entry points
```

### The thin harness (`harness/`)

One interface (`LLMClient`) with two adapters:

- **`openai_compat`** — talks to any OpenAI-compatible `/v1/chat/completions` endpoint:
  **Ollama** (`:11434/v1`), **llama.cpp server** (`:8080/v1`), **vLLM** (`:8000/v1`).
  This is the local + self-hosted path.
- **`anthropic`** — Claude **Opus 4.8** (`claude-opus-4-8`) via the official SDK
  (adaptive thinking, structured outputs). The BYOK/frontier path and the data-gen /
  judge engine.

The Python harness is for experimentation now; the **interface contract and the
`skills/` assets are the durable artifacts** that port to the C# product runtime later.

### The benchmark matrix (`benchmarks/`)

`{Gemma 4, Qwen 3.6} × {Q4, Q8} × {8k, 16k, 32k ctx} × {zero-shot, few-shot, CoT,
tool-augmented(HC), self-consistency}`, with **Opus 4.8 as the capability ceiling** and
LingGym's published numbers as an external anchor. Every cell logs **accuracy + output
tokens + latency + peak VRAM** → a leaderboard you can read as an intelligence ↔ cost ↔
offline-feasibility frontier.

Two task modes, **scored and reported separately** (never averaged together):

- **Discriminative** — MC gloss choice (LingGym-style).
- **Generative** — segment / gloss / produce surface form; scored by exact-match +
  HermitCrab round-trip.

---

## Three methodology guards (do not skip)

1. **Eval/train firewall.** Data that Opus *generates* for tuning a local model must
   never enter the *evaluation* set. Keep a human-validated, Opus-untouched gold
   holdout, or the benchmark measures circular leakage.
2. **Calibrate the judge.** Validate Opus-as-judge against human gold on a sample before
   trusting it to score or rank — report judge↔human agreement.
3. **Separate discriminative vs generative scores everywhere.** They answer different
   product questions and the harness affects them differently.

---

## Hardware notes (single RTX 3090, 24 GB)

- Gemma 4 (~27–31B) and Qwen 3.6 27B fit at **Q4 weights**, but **32K context is tight**
  — Ampere has no FP8, so the KV cache is the squeeze (comfortable 8–16K; 32K needs Q4 +
  INT8 KV cache).
- Q4 measurably dents hard reasoning vs Q8 — **sweep Q4 vs Q8 empirically**, don't assume.
- All local runtimes (Ollama / llama.cpp / vLLM) expose an OpenAI-compatible endpoint,
  which is what lets one harness drive local + hosted identically.

---

## Opus 4.8 for data generation (`data_gen/`)

`claude-opus-4-8`, 1M context. Offline batch jobs use the **Batch API (50% discount**,
async, supports prompt caching + structured outputs) to: augment the gold set, craft
preference/RL pairs (candidate analyses ranked by Opus-as-judge), and judge open-ended
generative output. **Cache the shared grammar/typology context once** and reuse across
thousands of items (cache reads ~0.1×). See `data_gen/README.md`.

---

## Quickstart

```bash
cd research
python -m venv .venv && . .venv/Scripts/activate   # Windows; use bin/activate on POSIX
pip install -e .
```

```powershell
# Local model: build ik_llama.cpp once, then serve a GGUF model (see ../serving/)
../serving/install-ik-llama.ps1
../serving/run-ik-llama-server.ps1 -Model D:\gguf\gemma-4-27b-IQ4_K.gguf -CtxSize 16384
```

```bash
# Smoke-test the local server (the 'ik_llama' endpoint → :8080/v1)
python scripts/smoke_test.py --endpoint ik_llama --prompt "Gloss the Swahili word 'ninakupenda'."

# Smoke-test Opus 4.8 (needs ANTHROPIC_API_KEY)
python scripts/smoke_test.py --endpoint opus --prompt "Gloss the Swahili word 'ninakupenda'."
```

Local serving is **ik_llama.cpp via `serving/` PowerShell scripts** (no Ollama required) —
chosen for direct GGUF quant control (incl. its IQ\*\_K quants) and because the server is
language-agnostic: the Python harness and later C# both just talk HTTP to `/v1`.

## First milestone

1. Stand up the harness (done — skeleton).
2. Wire LingGym's morphology+phonology subset (~1,481 items) into `benchmarks/fieldwork/`.
3. Run Gemma 4 27B Q4, Qwen 3.6 27B Q4, and Opus 4.8 on it; report the gap.
4. The headline finding: **local-vs-Opus gap on contaminated-MC vs uncontaminated-generative**.
