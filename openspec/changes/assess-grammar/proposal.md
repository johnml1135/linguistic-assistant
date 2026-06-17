## Why

Building a lexicon + morphology has many *workable* solutions but not equally *good* ones, and a 30B
(or BYOK) model needs an objective way to answer "what's the worst part of this grammar?", "is
solution A or B better?", and "should these rules/lexemes be split or combined?". FieldWorks exposes
the raw signals (per-wordform parse counts, the Predicted-Analyses ambiguity count, Parse-result
success/failure, the Try-A-Word trace) but **computes no aggregate score, no ranking, and no failure
taxonomy** — the judgment is left in the linguist's head. This change builds the missing layer:
deterministic, paper-backed measures plus an Occam (Minimum Description Length) objective, wrapped in
an assessor skill, gated by the golden set.

## What Changes

- Add **`research/assess/`** (Python first): a **metric scorecard** over the `hc` CLI + the golden
  harness — coverage, spurious ambiguity, gold round-trip accuracy (boundary P/R/F1 + exact-analysis),
  grammar size/description-length counts, generalization ratio, dead constructs, over-generation, a
  per-construct **"worst part" ablation ranking**, and productivity (Tolerance Principle).
- Add an **MDL model-selection** module: the two-part code `L(G) + L(D|G)` that scores grammars in
  bits and decides A-vs-B and split-vs-combine — Goldsmith/*Linguistica*'s exact criterion. Over-
  generation is penalized automatically (ambiguity costs bits).
- Add the **assess-grammar skill** (`linguistics/skills/assess-grammar.md`): consumes the scorecard +
  MDL, ranks the worst parts with linguistic rationale, recommends a refactor, and **requires the
  golden non-regression gate** before any recommendation is trusted.
- Add a **C# project (phase 2)** that computes the *same* measure definitions over **LibLCM** objects
  (read-only analysis of a real FieldWorks project), emitting the identical scorecard schema.
- Every measure is defined with an **exact formula and a citation**; the spec is the contract the
  Python and C# implementations both satisfy.

## Capabilities

### New Capabilities
- `assess-grammar-metrics`: the deterministic scorecard — each measure defined by exact calculation
  and reference (Approach A).
- `assess-grammar-mdl`: the Minimum Description Length objective and the model-selection decisions
  (better? split/combine?) it grounds (Approach B).
- `assess-grammar-skill`: the AI judgment layer that reasons over A + B (+ naturalness heuristics),
  prioritizes findings, and proposes gated refactors (Approach C).
- `liblcm-grammar-analyzer`: the C# read-only analyzer that computes the same measures over LibLCM
  (Approach A on real FLEx data; phase 2).

### Modified Capabilities
<!-- None — no existing OpenSpec specs define these. -->

## Impact

- **New code:** `research/assess/` (`metrics.py`, `mdl.py`, `scorecard.py`, CLI), driving
  `research/golden/hc.py` + the golden ablator and reusing `research/eval/` results conventions; a C#
  `SIL.LinguisticAssistant.GrammarAssess` analysis project (phase 2).
- **New skill:** `linguistics/skills/assess-grammar.md`, cross-linked to `read-the-gate`,
  `generalize-not-enumerate`, `productivity-restriction`.
- **References:** adds Rissanen (MDL), Goldsmith 2001 (Linguistica), Creutz & Lagus (Morfessor),
  Yang 2016 (Tolerance Principle), Dressler (Natural Morphology), SPE, SIGMORPHON-2022 segmentation —
  to be reflected in `linguistics/References.md`.
- **Depends on:** the `hc` verifier (`hermitcrab-net-verifier`) and the golden set (`golden-set`);
  guardrails inherited — never score on coverage alone; spurious ambiguity is first-class; every
  recommended change passes the golden gate.
- **Out of scope:** auto-applying refactors; the `.fwdata` write path; RL.
