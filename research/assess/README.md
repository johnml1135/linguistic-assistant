# assess/

Approach A of the `assess-grammar` spec: the **deterministic grammar-assessment scorecard**. Computes
paper-backed quality measures over a HermitCrab grammar (golden `LangModel` + the `hc` CLI) and over
LibLCM/LIFT data, and ranks the **worst parts** of a grammar by leave-one-out.

## Modules
- `metrics.py` — pure-math measures (testable offline): coverage (type/token), spurious ambiguity
  (mean / rate / average-parse-base), gold round-trip (exact-analysis recall) + boundary P/R/F1,
  over-generation + non-regression, grammar size, generalization ratio, dead constructs, productivity
  (Tolerance Principle `e ≤ N/ln N`).
- `inventory.py` — construct inventories from `golden.LangModel`, a **LibLCM `.fwdata` XML** dump
  (read-only, by class local-name), or a **LIFT** export.
- `builders.py` — assemble a full `Scorecard`: `assess_hermitcrab` (parse-based + structural via `hc`),
  `assess_liblcm` / `assess_lift` (structural-only; no parser).
- `worst_part.py` — `worst_part_ranking`: leave-one-out `worstness_metrics(c) = λ·cost − benefit`
  (higher = worse). Reuses the golden grammar/ablation model; `parse_fn` injectable for offline tests.
- `scorecard.py` — the deterministic JSON schema (sorted keys, no timestamps, content hash) shared with
  the future C# `liblcm-grammar-analyzer`.
- `assess.py` — CLI. `tests_smoke.py` — offline tests (run `python research/assess/tests_smoke.py`).

## Run
```bash
python research/assess/assess.py --source demo                       # offline: full scorecard + worst-part, no hc
python research/assess/assess.py --source liblcm --path project.fwdata   # structural scorecard from LibLCM
python research/assess/assess.py --source lift   --path lexicon.lift     # lexicon-only counts
python research/assess/assess.py --source hermitcrab --lang lez          # full scorecard (needs the hc CLI)
```

## Key facts / boundaries
- **Boundary-F1 is skipped on the HC path** — HermitCrab echoes corrupted morph *forms* (golden/hc.py),
  so gloss-line exact-analysis recall is the reliable correctness; `boundary_prf` is for LibLCM or any
  source with trustworthy segmentation.
- **Parse-based measures need a parser.** LibLCM/LIFT give structural measures only; for coverage/
  ambiguity/round-trip on a real FLEx project, build an HC grammar from it and use `assess_hermitcrab`.
- **MDL (Approach B)** and the **assessor skill (Approach C)** are the next phases — this is A.
- Every measure cites its source in code; see `openspec/changes/assess-grammar/` for the spec + references.
