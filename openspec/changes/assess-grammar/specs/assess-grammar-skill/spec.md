## ADDED Requirements

This is the AI judgment layer (`linguistics/skills/assess-grammar.md`). It consumes the deterministic
outputs of `assess-grammar-metrics` and `assess-grammar-mdl` and turns numbers into prioritized,
linguistically-reasoned findings — but it never certifies on its own opinion; the binding verdicts are
the deterministic metrics, the MDL objective, and the golden gate.

### Requirement: Answer the three assessment questions from the deterministic evidence
The skill SHALL answer (1) "what is the worst part of the grammar?" from the per-construct ranking
(metrics `net(c)` and MDL `ΔDL(c)`), (2) "is solution A or B better?" from `DL` (lower wins), with the
metric scorecard as supporting evidence, and (3) "should these be split or combined?" from the MDL
split-vs-merge `ΔDL`. The skill SHALL cite the specific numbers it relied on in each finding.

#### Scenario: Worst-part answer is evidence-backed
- **WHEN** asked for the worst part
- **THEN** the skill returns the lowest-`net(c)` / negative-`ΔDL(c)` constructs with their coverage,
  ambiguity, size, and ΔDL figures, not an unsupported opinion

### Requirement: Naturalness rubric for explanation and MDL tie-breaks
The skill SHALL apply a naturalness rubric — transparency, iconicity, bi-uniqueness, and productivity
(via the Tolerance Principle from `assess-grammar-metrics`) — to *explain* findings and to break ties
**only** when candidates are within-tolerance-equal on `DL` and equal on `worstness` rank (e.g.
rule-governed alternation vs suppletion at comparable `DL`), and SHALL prefer feature-defined natural
classes over arbitrary segment lists. These are advisory heuristics layered on the binding metrics; when
`DL` separates the candidates, `DL` wins and naturalness is explanatory only. (Naturalness: Dressler et al. 1987, *Leitmotifs in Natural Morphology*;
feature economy / natural classes: Chomsky & Halle 1968, *SPE*.)

#### Scenario: Suppletion vs rule tie broken by naturalness
- **WHEN** two analyses have near-equal `DL`
- **THEN** the skill uses transparency/productivity to recommend one and states it is a naturalness tie-break

### Requirement: Recommendations are gated, never auto-trusted
Any refactor the skill recommends SHALL be emitted as a change-set and SHALL pass the golden
non-regression gate (previously-correct forms still parse, no new spurious analyses, golden exact-
analysis recall not reduced) before it is reported as accepted. A refactor that *reduces* coverage or
that trades coverage for ambiguity SHALL be accepted only if total description length `DL` decreases
(the information-theoretic net is favorable) — so a small coverage loss is permitted only when spurious
ambiguity drops by more. The skill's reasoning is non-deterministic; the deterministic metrics + `DL` +
gate are binding. (`read-the-gate`; `golden-set` non-regression; MDL net from `assess-grammar-mdl`.)

#### Scenario: A plausible refactor that regresses the gate is rejected
- **WHEN** the skill proposes a rule that lowers size but breaks a previously-correct parse
- **THEN** the recommendation is marked rejected-by-gate and not presented as an improvement

### Requirement: Determinism boundary is explicit
The skill SHALL treat its prose assessment as advisory and the deterministic scorecard, MDL figures,
and golden gate verdict as binding: the assessment MAY vary by model/run, but the skill SHALL NEVER
report a quality verdict that is not backed by those deterministic artifacts.

#### Scenario: Verdicts trace to deterministic artifacts
- **WHEN** the skill states "B is better than A"
- **THEN** that claim is backed by the reported `DL(A)`, `DL(B)`, and gate results, not by model opinion alone
