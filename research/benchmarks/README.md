# benchmarks/

Scores `(model × quantization × harness-config)` on word-level morphology/phonology.

## Two task modes — scored and reported SEPARATELY

- **Discriminative** (`linggym/`, and an MC mode over fieldwork data): pick the correct
  gloss/segmentation from candidates. Cheap, fast, what LingGym measures. Contaminated
  and mostly syntax — a calibration baseline, not the target.
- **Generative** (`fieldwork/`): produce a segmentation / gloss / surface form. Scored
  by exact-match + HermitCrab round-trip. This is the product-relevant task and where
  harness design (few-shot, CoT, tool-augmentation, self-consistency) actually pays off.

Never average the two into one number.

## The matrix

`{Gemma 4, Qwen 3.6} × {Q4, Q8} × {8k, 16k, 32k ctx} × {zero-shot, few-shot, CoT,
tool-augmented(HC), self-consistency}`, plus **Opus 4.8** as the capability ceiling and
LingGym's published numbers as an external anchor.

`runner.py` (TODO) sweeps the matrix and writes a leaderboard to `results/` with, per
cell: **accuracy, output tokens, latency, peak VRAM**.

## Caveats baked in

- CoT barely moved LingGym's MC scores — expect harness payoff on the **generative**
  task, not MC.
- Q4 dents hard reasoning vs Q8 — report both; don't assume.
- LingGym scores **overstate** real-world capability (training contamination); the
  uncontaminated fieldwork set is the one to trust.

## Subfolders

- `linggym/` — external calibration. CC-BY-4.0 data from `changbingY/LingGym`. **Bootstrap
  source**: its ~1,481 morphology+phonology items seed `fieldwork/` until real FLEx data
  is extracted (`../data_prep/`).
- `fieldwork/` — PRIMARY benchmark. Morphology/phonology, both task modes.
- `results/` — committed leaderboards (Parquet/CSV) + generated reports.
