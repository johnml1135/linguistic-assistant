# models/

Model + quantization configs and launch notes for the local benchmark candidates.

## Candidates (single RTX 3090, 24 GB)

| Model | Sizes of interest | Notes |
|---|---|---|
| **Gemma 4** | ~27–31B | Q4 weights fit; sweep Q4 vs Q8 |
| **Qwen 3.6** | 27B (also 35B-A3B MoE) | Q4 weights fit; MoE is lighter on active params |

## VRAM reality (24 GB, Ampere)

- Q4 weights fit (~17–19 GB). **32K context is tight** — no FP8 on Ampere, so the KV
  cache is the squeeze. Comfortable at 8–16K; 32K needs Q4 + INT8 KV cache.
- **Sweep Q4 vs Q8 empirically** — Q4 measurably dents hard reasoning; don't assume the
  bigger-model-at-Q4 wins on these tasks.

## Serving (pick one; all expose an OpenAI-compatible endpoint)

- **Ollama** — easiest; `:11434/v1`. GGUF quants.
- **llama.cpp** (`llama-server`) — most quant flexibility; `:8080/v1`. GGUF.
- **vLLM** — fastest, best structured-output enforcement; `:8000/v1`. AWQ/GPTQ.

Point the harness at whichever via `harness/config.py`.

TODO:
- [ ] Pin exact model tags/quant files per candidate (record for reproducibility).
- [ ] Launch scripts + a VRAM-probe helper to log peak usage per matrix cell.
