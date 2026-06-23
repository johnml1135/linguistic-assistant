# A/B results — harness improvements (LingGym, N=200, seed 13, greedy, no-think)

Same 200 items across all arms (paired). Δ vs baseline; McNemar exact two-sided p (paired).
Caveat: contaminated, near-ceiling — see harness_research.md.


## gemma31b

| arm | acc | Δ vs base | McNemar p | note |
|---|---|---|---|---|
| baseline | 0.855 | – | – | reference |
| logprob | 0.850 | -0.005 | 1.00 | ns (b=1,c=0) |
| prior | 0.850 | -0.005 | 1.00 | ns (b=1,c=0) |
| permute | 0.865 | +0.010 | 0.73 | ns (b=3,c=5) |
| fewshot | 0.880 | +0.025 | 0.30 | ns (b=5,c=10) |
| skill | 0.870 | +0.015 | 0.61 | ns (b=6,c=9) |

## qwen36

| arm | acc | Δ vs base | McNemar p | note |
|---|---|---|---|---|
| baseline | 0.825 | – | – | reference |
| logprob | 0.825 | +0.000 | 1.00 | ns (b=0,c=0) |
| prior | 0.825 | +0.000 | 1.00 | ns (b=0,c=0) |
| permute | 0.855 | +0.030 | 0.07 | ns (b=1,c=7) |
| fewshot | 0.840 | +0.015 | 0.61 | ns (b=6,c=9) |
| skill | 0.840 | +0.015 | 0.55 | ns (b=4,c=7) |
| combo | 0.850 | +0.025 | 0.44 | ns (b=11,c=16) |

## Best per model
- **gemma31b: fewshot** (0.880)
- **qwen36: permute** (0.855)
