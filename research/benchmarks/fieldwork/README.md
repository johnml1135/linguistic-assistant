# benchmarks/fieldwork/

The **primary** benchmark: word-level morphology/phonology on real (uncontaminated)
data. Two modes, scored separately:

- **Discriminative** — choose the correct gloss/segmentation from candidates.
- **Generative** — produce the segmentation / gloss / surface form; scored by
  exact-match + HermitCrab round-trip (generate the surface form, compare to attested).

## Data sources (in order of trust)

1. **FLEx-derived gold** (`../../data_prep/`): `{word, segmentation, gloss, provenance}`
   from a real FieldWorks project. Uncontaminated and on-distribution — the set to trust.
2. **Bootstrap** (now): LingGym's morphology+phonology subset (`../linggym/`) while FLEx
   extraction is arranged.

## Methodology guards (enforced here)

- **Eval/train firewall** — items that Opus *generated* for tuning (`../../data_gen/`)
  must never appear in this eval set. Keep an Opus-untouched human-validated holdout.
- **Calibrate the judge** — when scoring generative output with Opus-as-judge, report
  judge↔human agreement on a sample first.

TODO:
- [ ] Normalized item schema (shared with `linggym/`).
- [ ] Generative scorer: exact-match + HermitCrab round-trip hook.
- [ ] Holdout manifest + provenance tracking (firewall enforcement).
