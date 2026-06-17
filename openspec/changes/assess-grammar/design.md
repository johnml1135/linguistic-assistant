## Context

FieldWorks surfaces raw parse signals but no aggregate score, ranking, or failure taxonomy (confirmed
2026-06: per-wordform Predicted-Analyses count, Parse-result success/failure, Try-A-Word trace, Grammar
Sketch — all interpreted by hand). The repo already has the pieces to compute real measures: the `hc`
CLI verifier (`hermitcrab-net-verifier`), the golden set + ablator + round-trip (`golden-set`), and the
`eval-proposal-loop` harness/results conventions. This change defines the measures (with exact formulas
and citations), an MDL objective for "which is better", and the assessor skill — Python first, a C#
LibLCM analyzer second.

## Goals / Non-Goals

**Goals:**
- A deterministic, paper-backed **scorecard** (Approach A) computed from `hc` + golden.
- A principled **MDL** objective (Approach B) for better?/split-or-combine?.
- An **assessor skill** (Approach C) that prioritizes findings and proposes *gated* refactors.
- One measure definition, two implementations (Python now, C# over LibLCM later).
- Every measure traceable to a citation that the implementation accurately represents.

**Non-Goals:** auto-applying refactors; `.fwdata` writes; RL; replacing the golden scorer (this assesses
*grammar quality*, the golden scorer rewards *proposals* — complementary).

## Decisions

- **Three approaches compose; build A → B → C.** A is the substrate (the numbers FLEx makes you compute
  by hand); B is the principled Occam objective and the headline differentiator; C is the judgment skill.
  *Alternative:* skip straight to an LLM judge — rejected; without deterministic A/B the verdicts aren't
  trustworthy or reproducible.
- **MDL is an estimator with a versioned encoding scheme.** `L(G)`/`L(D|G)` are coding-dependent
  (Goldsmith/Morfessor both pick a coding). We document the coding, version it, and never compare `DL`
  across coding versions. *Alternative:* a single ad-hoc weighted size — that's the A proxy; B exists
  precisely to remove hand-tuned weights.
- **HC is rule-based, not a probability model**, so `L(D|G)` uses a unigram morph model estimated from
  analysed counts plus an explicit `log2|hc(w)|` disambiguation term. This is an approximation, stated as
  such; it has the right qualitative behavior (over-generation costs bits).
- **Worst-part ranking reuses the golden ablator** (leave-one-out). Both rankings use a "higher = worse"
  orientation — A's `worstness_metrics(c) = λ·cost(c) − benefit(c)` and B's `worstness_mdl(c) = −ΔDL(c)`
  — and "agree in direction" is defined operationally as a **positive rank correlation** (Spearman ρ > 0)
  on the golden set (the consistency check, task 6.3).
- **Guardrails are normative, not advice:** coverage never standalone; spurious ambiguity first-class;
  every recommended refactor passes the golden non-regression gate and must not raise ambiguity.
- **Layout:** Python `research/assess/` = `metrics.py` (A), `mdl.py` (B), `scorecard.py` (schema + JSON),
  `worst_part.py` (ablation ranking), CLI `assess.py`; reuses `research/golden/hc.py` + the ablator.
  Skill at `linguistics/skills/assess-grammar.md`. C# `SIL.LinguisticAssistant.GrammarAssess` (phase 2,
  read-only LibLCM) emits the same scorecard schema, asserted against a shared fixture.

## References (to be reflected in linguistics/References.md)

- **Rissanen, J. (1978).** "Modeling by shortest data description." *Automatica* 14(5): 465–471. — MDL.
- **Goldsmith, J. (2001).** "Unsupervised Learning of the Morphology of a Natural Language."
  *Computational Linguistics* 27(2): 153–198. — *Linguistica*; two-part MDL for morphology; signatures;
  the merge/split/posit-rule heuristics.
- **Creutz, M. & Lagus, K. (2007).** "Unsupervised models for morpheme segmentation and morphology
  learning." *ACM TSLP* 4(1). — Morfessor; MDL as MAP (`−log p(G) − log p(D|G)`).
- **de Marcken, C. (1996).** *Unsupervised Language Acquisition.* PhD thesis, MIT. — MDL lexicon induction.
- **Chomsky, N. & Halle, M. (1968).** *The Sound Pattern of English.* Harper & Row. — the evaluation
  metric (fewer symbols / feature economy / natural classes).
- **Yang, C. (2016).** *The Price of Linguistic Productivity.* MIT Press. — the Tolerance Principle:
  a rule over `N` items with `e` exceptions is productive iff `e ≤ N / ln N`.
- **Dressler, W. U., Mayerthaler, W., Panagl, O. & Wurzel, W. U. (1987).** *Leitmotifs in Natural
  Morphology.* John Benjamins. — naturalness: transparency, iconicity, bi-uniqueness, productivity.
- **Batsuren, K. et al. (2022).** "The SIGMORPHON 2022 Shared Task on Morpheme Segmentation."
  *SIGMORPHON (NAACL).* — boundary precision/recall/F1; over-splitting/precision hazard.
- **Carroll, J. & Briscoe, T. (1998).** "Parser Evaluation: a Survey and a New Proposal." *LREC.* —
  the Average Parse Base (geometric-mean parse count), adapted here to word-level analyses.

## Risks / Trade-offs

- **MDL coding sensitivity** → version the coding; report `L(G)`/`L(D|G)` separately; compare only within
  a coding version; validate that A's proxy and B's `DL` agree in direction on the golden set.
- **`L(D|G)` is an approximation** (HC isn't probabilistic) → document the unigram+disambiguation model;
  treat absolute bits as relative, not physical.
- **Average-Parse-Base** is the geometric-mean parse count from parser evaluation (Carroll & Briscoe
  1998), used here at word level — keep it as a relative ambiguity index, not an absolute.
- **Tolerance-Principle inputs are hard** (counting `N` eligible items / `e` exceptions per rule from HC
  data is non-trivial) → start with rules where the eligible class is well-defined; flag others as
  "productivity not computable".
- **Misrepresenting a paper** is the headline risk this change guards against → cross-review agents verify
  every formula/claim against the source before implementation.

## Open Questions

- Default weights `w_t` for the size proxy and `λ` for `net(c)` (calibrate on golden).
- Exact `L(G)` coding for HC rules/affix-processes (structural cost per rule).
- Whether boundary-F1 alignment uses best-analysis or gold-analysis alignment when HC is ambiguous.
