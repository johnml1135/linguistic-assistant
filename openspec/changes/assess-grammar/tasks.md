## 1. References & scaffolding

- [x] 1.1 Add the 9 references (Rissanen 1978, Goldsmith 2001, Creutz & Lagus 2007, de Marcken 1996,
  Chomsky & Halle 1968, Yang 2016, Dressler et al. 1987, Batsuren et al. 2022, Carroll & Briscoe 1998)
  to `linguistics/References.md` (new §11 "Grammar evaluation — MDL, productivity, parser metrics").
- [x] 1.2 Create `research/assess/` package; define `scorecard.py` (the deterministic JSON schema +
  content hash) shared by all measures and by the future C# analyzer.

## 2. Approach A — metric scorecard (Python)

- [x] 2.1 `metrics.py`: coverage (type/token), spurious ambiguity (mean / rate / average-parse-base) —
  computed from `golden/hc.py` outputs over a corpus.
- [x] 2.2 Gold round-trip: exact-analysis recall + `boundary_prf` (SIGMORPHON-2022); boundary-F1 skipped
  on the HC path (corrupted morph forms) per spec note, available for LibLCM/reliable segmentation.
- [x] 2.3 Grammar size counts per construct type + weighted size `S`; generalization ratio; dead constructs.
- [x] 2.4 Over-generation + `non_regression` check.
- [x] 2.5 `worst_part.py`: leave-one-out per-construct `worstness_metrics(c)` ranking (golden model/ablation).
- [x] 2.6 Productivity (Tolerance Principle `e ≤ N/ln N`); returns "not-computable" when `N<2`/undefinable.
- [x] 2.7 CLI `assess.py` (+ `--source demo` offline) + `tests_smoke.py` (deterministic scorecard; 9 tests).

## 3. Approach B — MDL objective (Python)

- [x] 3.1 `mdl.py`: `L(G)` from the documented, versioned (`ENCODING_VERSION`) encoding scheme
  (morpheme form length-coding `(len+1)·log2(|Σ|+1)` + affix/lexeme structural cost).
- [x] 3.2 `L(D|G)` = unigram morph NLL + `log2|hc(w)|` disambiguation term (+ verbatim fallback for
  unparseable words); report `L(G)`, `L(D|G)`, `DL` separately.
- [x] 3.3 Model-selection: `better_grammar` (lower DL) + `decide_split_or_combine`; wired into the
  scorecard via `assess_hermitcrab(with_mdl=True)`.
- [x] 3.4 Marginal `worstness_mdl(c) = DL(G) − DL(G\{c})` ranking + `spearman`; test asserts positive
  rank correlation with A's `worstness_metrics(c)` on the demo (`tests_smoke.py`, 12 tests).

## 4. Approach C — assessor skill

- [ ] 4.1 `linguistics/skills/assess-grammar.md` (the judgment skill; cross-link `read-the-gate`,
  `generalize-not-enumerate`, `productivity-restriction`).
- [ ] 4.2 Driver that runs A + B on a grammar, ranks worst parts, answers better?/split-or-combine?, and
  emits any refactor as a change-set gated by the golden non-regression + no-ambiguity-increase check.
- [ ] 4.3 Naturalness rubric (Dressler) + SPE feature-economy as advisory tie-breakers over the binding metrics.

## 5. Phase 2 — C# LibLCM analyzer

- [ ] 5.1 `SIL.LinguisticAssistant.GrammarAssess` (net10, read-only): enumerate LibLCM constructs and
  compute the `assess-grammar-metrics` measures, emitting the same scorecard JSON schema.
- [ ] 5.2 Parity test: Python and C# scorecards agree on a shared fixture (exact for counts).

## 6. Cross-review & calibration

- [ ] 6.1 Cross-review the spec for internal consistency and faithful representation of every cited paper
  (the formulas in §metrics/§mdl match the sources); fix any misrepresentation.
- [ ] 6.2 Calibrate `w_t`, `λ`, and the `L(G)` rule-cost on the golden languages; record chosen values.
- [ ] 6.3 Confirm a positive rank correlation (Spearman ρ > 0) between A's `worstness_metrics(c)` and
  B's `worstness_mdl(c)` on the golden set (the "agree in direction" check).
