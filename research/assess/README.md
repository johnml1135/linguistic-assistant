# assess/

Approaches **A (metric scorecard)** and **B (MDL objective)** of the `assess-grammar` spec. Computes
paper-backed quality measures over a HermitCrab grammar (golden `LangModel` + the `hc` CLI) and over
LibLCM/LIFT data, ranks the **worst parts** of a grammar two ways, and grounds the
**"better? / split-or-combine?"** decision in Minimum Description Length (bits).

## Modules
- `metrics.py` — Approach A pure-math measures (testable offline): coverage (type/token), spurious
  ambiguity (mean / rate / average-parse-base), gold round-trip (exact-analysis recall) + boundary
  P/R/F1, over-generation + non-regression, grammar size, generalization ratio, dead constructs,
  productivity (Tolerance Principle `e ≤ N/ln N`).
- `mdl.py` — Approach B: the two-part code `DL = L(G) + L(D|G)` (Goldsmith 2001 / Rissanen 1978 /
  Morfessor). `description_length`, `better_grammar`, `decide_split_or_combine`, `worstness_mdl_ranking`,
  and `spearman` (the cross-approach "agree in direction" check). Encoding is **versioned**
  (`ENCODING_VERSION`); `DL` is comparable only within a version.
- `inventory.py` — construct inventories from `golden.LangModel`, a **LibLCM `.fwdata` XML** dump
  (read-only, by class local-name), or a **LIFT** export.
- `builders.py` — assemble a full `Scorecard`: `assess_hermitcrab` (parse-based + structural + MDL via
  `hc`), `assess_liblcm` / `assess_lift` (structural-only; no parser).
- `worst_part.py` — `worst_part_ranking`: Approach-A leave-one-out `worstness_metrics(c) = λ·cost −
  benefit` (higher = worse). `parse_fn` injectable for offline tests.
- `scorecard.py` — the deterministic JSON schema (sorted keys, no timestamps, content hash) shared with
  the future C# `liblcm-grammar-analyzer`.
- `assess.py` — CLI. `tests_smoke.py` — offline tests (12; run `python research/assess/tests_smoke.py`).

## "Which grammar is better?" / "split or combine?"
Build the two candidate `LangModel`s, score each with `mdl.description_length(...)["DL"]`, and call
`mdl.better_grammar({...})` / `mdl.decide_split_or_combine(dl_combined, dl_split)` — lower bits wins.
Over-generation is charged automatically (the `log2|hc(w)|` term in `L(D|G)`).

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
- **Approaches A + B are implemented here.** The **assessor skill (Approach C)** and the **C#
  `liblcm-grammar-analyzer`** are the next phases.
- The MDL `L(D|G)` is an approximation (HC isn't a probability model): a unigram morph model + a
  `log2|hc(w)|` disambiguation term, with a verbatim fallback for unparseable words. Treat `DL` as a
  relative score within one `ENCODING_VERSION`, not a physical bit count.
- Every measure cites its source in code; see `openspec/changes/assess-grammar/` for the spec + references.
