# data_gen/

Offline **Claude Opus 4.8** batch jobs that manufacture data the benchmark and future
local-model tuning need.

## Jobs

1. **Augment the gold set** — generate harder cases / MC distractors from raw FLEx
   interlinear → fuel for `../benchmarks/`.
2. **Preference / RL pairs** — generate candidate analyses, rank them with Opus-as-judge
   → fuel for later DPO/SFT of a local model.
3. **LLM-as-judge** — score open-ended generative outputs where exact-match is too brittle.

## How (Batch API + caching)

- Model `claude-opus-4-8`. Use the **Batch API** (50% discount, async, up to 100k
  requests/batch) for volume jobs.
- **Prompt-cache the shared context** (the grammar, typological references, the
  instruction block) once and reuse across thousands of items — cache reads ~0.1×.
- Use **structured outputs** (`output_config.format` with a JSON schema) for typed items.
- Note: server-side refusal-fallback is not available *inside* batches (irrelevant here).

## Methodology guards (non-negotiable)

- **Eval/train firewall** — anything generated here for *tuning* must never enter the
  *evaluation* gold. Track provenance; keep an Opus-untouched human-validated holdout.
- **Calibrate the judge** — validate Opus-as-judge against human gold on a sample and
  report agreement before trusting its scores/rankings.

TODO:
- [ ] Batch job: gold-set augmentation (cached shared context, structured items).
- [ ] Batch job: candidate-generation + judge-ranking → preference pairs.
- [ ] Judge-calibration harness (Opus vs. human agreement on a sample).
