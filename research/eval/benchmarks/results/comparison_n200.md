# LingGym replication — real local runs (RTX 3090, ik_llama.cpp)

Task: Word-Gloss Inference, full **S+G+KP+T** condition (verbatim released prompt).
Decoding: **greedy** (matches the released script). Reasoning/thinking **disabled** (`--reasoning off`).
Slice: first **200** items (deterministic file order — Fwe + start of Gyeli), identical for both models.
Served as GGUF via a CUDA build of ik_llama.cpp (`-DGGML_CUDA=ON`, arch 86).

| Model | Quant | Accuracy | Unparsed | Time |
|---|---|---|---|---|
| Gemma 4 31B-it QAT | q4_0 (official QAT) | **0.825** | 0 | 79.7s |
| Qwen 3.6 27B-it | Q4_K_M | **0.845** | 0 | 123.2s |

## Per-language (within the 200-item slice)

| Language | Gemma 4 31B QAT | Qwen 3.6 27B |
|---|---|---|
| Fwe | 120/147 (0.82) | 128/147 (0.87) |
| Gyeli | 45/53 (0.85) | 41/53 (0.77) |

## Caveats
- 200-item slice, not the full 19,612 (the full set at ~0.5-1 s/item is hours per model).
- LingGym is contamination-inflated and ~85% syntax; this validates the harness end-to-end
  on real models and gives paper-comparable numbers, not the real-world morph/phon signal.
- Greedy + no-think for fidelity/speed; the paper's appendix used sampling (see presets.py `paper`).
