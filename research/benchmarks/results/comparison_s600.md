# LingGym replication - representative run vs. the paper

Real local runs on an RTX 3090 via a CUDA build of ik_llama.cpp.

- **Task / condition:** Word-Gloss Inference, full **S+G+KP+T** (verbatim released prompt).
- **Sample:** 600 items drawn at random (seed 0) from the full 19,612 - spans all 18
  languages roughly proportionally (so syntax-dominated, like the full set). Identical
  items for both models.
- **Decoding:** greedy (matches the released eval script). Thinking disabled (`--reasoning off`).
- **Quant:** Gemma = official QAT q4_0; Qwen = Q4_K_M.

## Headline

| Model (ours, local) | Accuracy (n=600) | 95% CI |
|---|---|---|
| Gemma 4 31B-it QAT (q4_0) | **0.842** | ~+/-2.9 pp |
| Qwen 3.6 27B-it (Q4_K_M) | **0.852** | ~+/-2.9 pp |

The two overlap within sampling noise - **statistically indistinguishable here**.
(0 unparsed in both runs.)

## vs. the paper's S+G+KP+T numbers (Table 3)

| Model | Paper acc | Note |
|---|---|---|
| **Qwen 3.6 27B (ours)** | **85.2** | newer gen |
| **Gemma 4 31B QAT (ours)** | **84.2** | newer gen |
| DeepSeek-R1-32B | 81.17 | paper's best |
| LLaMA3-70B | 78.25 | |
| Qwen2.5-32B | 78.29 | prior gen of Qwen |
| Gemma3-27B | 77.02 | prior gen of Gemma |
| GPT-4o-mini | 73.88 | |
| Gemma3-12B | 73.97 | |
| Qwen2.5-7B | 71.09 | |

So **both our models beat every model in the paper at this condition**, including its best
(DeepSeek-R1-32B, 81.17). Same-family deltas: Gemma 4 31B QAT vs Gemma3-27B = **+7.2 pp**;
Qwen 3.6 27B vs Qwen2.5-32B = **+6.9 pp**.

## How to read that - caveats (important)

1. **Different model generations.** Gemma 4 != Gemma 3, Qwen 3.6 != Qwen 2.5. Newer models
   beating older ones is expected; this is not a like-for-like reproduction.
2. **Contamination is almost certainly worse for us, not better.** LingGym released Nov 2025;
   Gemma 4 / Qwen 3.6 are mid-2026 models, so they may have trained on LingGym itself (and
   more of its source grammars) than the paper's models did. "Beats SOTA" is therefore
   **not a capability claim** - it is consistent with memorization. This is exactly why the
   uncontaminated FLEx morph/phon set is the real signal.
3. **Sample, not full set.** 600 of 19,612 (~+/-3 pp). Syntax-dominated (~85%).
4. **Quant + greedy + no-think** vs the paper's fp16/sampling - minor, comparable regime.

## Per-language (this 600 slice)

| Language | N | Gemma 4 31B QAT | Qwen 3.6 27B |
|---|---|---|---|
| Pichi | 133 | 0.850 | 0.850 |
| Yauyos_Quecha | 114 | 0.886 | 0.851 |
| Mauwake | 57 | 0.807 | 0.930 |
| Ulwa | 49 | 0.776 | 0.816 |
| Palula | 49 | 0.714 | 0.776 |
| Rapa_Nui | 44 | 0.886 | 0.886 |
| Papuan_Malay | 31 | 0.903 | 0.903 |
| Kalamang | 22 | 0.864 | 0.864 |
| Kagayanen | 21 | 0.905 | 0.905 |
| Gyeli | 19 | 0.789 | 0.789 |
| Tuatschin | 19 | 0.947 | 0.789 |
| Moloko | 18 | 0.889 | 0.944 |
| Japhug | 16 | 0.875 | 0.750 |

## Error signal (both models missed)

456/595 both correct; 42 both-missed; 97 disagreements. The shared misses cluster on
fine morphosyntactic distinctions, not vocabulary:
- **clitic / case distinctions** (Ulwa `=ka` "in" vs `=u` "from"; Mauwake `nain` vs `nain=ko`
  bare demonstrative vs +NF clitic),
- **TAM / information-structure clitics** (Quechua `-qa` TOP present or not),
- **ignoring a decisive translation cue** (Pichi: gloss blank for "pay", translation says
  "you have to pay them", both chose "wonder").

These point directly at the skill ideas (glossing-abbreviation decoding, concord checking,
translation-grounding) - see the brainstorm.
