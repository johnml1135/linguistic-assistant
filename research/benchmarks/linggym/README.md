# benchmarks/linggym/

External calibration baseline + wiring smoke-test.

- **Source:** [`changbingY/LingGym`](https://github.com/changbingY/LingGym) (EMNLP 2025).
  19,612 multiple-choice word-gloss inference items from 18 reference grammars.
- **License:** CC-BY-4.0 (attribute on use).
- **Why it's only a baseline:** 85% syntax / 7% morphology / 0.36% phonology, and
  contaminated (models trained on the source grammars). Use it to anchor against the
  paper's numbers and to confirm the harness is wired correctly — not as the target.

## Bootstrap plan

Filter to the **morphology + phonology** subset (~1,481 items) and use it to seed the
`fieldwork/` benchmark until uncontaminated FLEx data is extracted via `../../data_prep/`.

TODO:
- [ ] Vendor or fetch the dataset (record the commit/version for reproducibility).
- [ ] Loader → normalized item schema shared with `fieldwork/`.
- [ ] Subset filter (field ∈ {morphology, phonology}).
- [ ] Scorer for the MC (discriminative) mode.
