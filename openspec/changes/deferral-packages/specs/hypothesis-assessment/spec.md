## ADDED Requirements

### Requirement: "Better hypothesis" decided by grammar-quality metrics (reuse research/assess/)
The system SHALL decide which hypothesis is better using the existing grammar-quality metrics in
`research/assess/` applied as a delta over the hypothesis edit — primarily **ΔMDL** (`L(G)+L(D|G)`, which
penalizes over-generation and grounds split-vs-combine), with the scorecard deltas (coverage, spurious
ambiguity, generalization ratio, over-generation, and **productivity / Tolerance Principle**). It SHALL NOT
redefine these measures; it consumes the `assess-grammar` definitions and SHALL run the golden
non-regression gate before trusting a recommendation.

#### Scenario: ΔMDL selects the better grammar
- **WHEN** hypotheses A and B both fix the focus
- **THEN** the one with the lower total description length (fewer bits, less over-generation) is ranked better

#### Scenario: Tolerance Principle decides rule-vs-exceptions
- **WHEN** a candidate rule's exceptions exceed Yang's tolerance threshold
- **THEN** assessment prefers listing the forms (or a narrower rule) over the over-broad rule

### Requirement: Metrics are presented, not just the verdict
The ticket SHALL show, per hypothesis, the metric deltas a linguist reasons about — ΔMDL (bits), coverage
gained, ambiguity added, over-generation, productivity vs tolerance, and the worst-part rank addressed —
so the reviewer sees WHY one hypothesis is better, alongside the concrete reparse edge cases.

#### Scenario: A hypothesis shows its metric profile
- **WHEN** a hypothesis is presented
- **THEN** its ΔMDL and scorecard deltas are shown next to its reparse consequences

### Requirement: Net parse delta over the corpus, with regression detection
The system SHALL assess a hypothesis by applying its edit, re-parsing a representative corpus slice, and
computing **net parse delta = (forms newly parsing correctly) − (forms that regressed: previously parsed,
now fail or mis-parse)**. Assessment SHALL report gains, regressions, and net.

#### Scenario: A fix with regressions is penalised
- **WHEN** hypothesis B parses the focus form but breaks 12 previously-parsing forms
- **THEN** assessment reports −net (or low net) and does not rank B as acceptable

### Requirement: Acceptance criteria
A hypothesis SHALL be deemed acceptable only if it (a) parses the focus form, (b) has non-negative net
parse delta, and (c) causes no high-impact regression. Deterministic scoring SHALL apply these gates before
any LLM verdict.

#### Scenario: True fix accepted
- **WHEN** the hypothesis is the correct edit (ablation ground truth)
- **THEN** it fixes the focus, has net ≥ 0, no high-impact regression, and is marked acceptable

### Requirement: LLM verdict is gated by the deterministic result
An LLM verdict on a hypothesis SHALL be presented the HC delta (gains/regressions/sample parses) and SHALL
NOT override the deterministic regression gate: the model may rank or explain among hypotheses that pass
the gates, but cannot accept one the regression check rejected.

#### Scenario: Model cannot accept a regressing hypothesis
- **WHEN** the model favours a hypothesis that the regression gate rejected
- **THEN** that hypothesis stays rejected; the model's preference is recorded but not applied

### Requirement: Restrictiveness scoring (subset principle)
When multiple hypotheses fix the focus with non-negative net delta, assessment SHALL prefer the most
RESTRICTIVE — the smallest licensed surface set that still covers the evidence — scored by over-generation
on held-out forms and the conditioning specificity of the rule. A broad "globbing" rule SHALL be penalised
relative to narrower rules (or an archiphoneme-collapse that round-trips) by its over-generation. When a
narrow set and a broad rule are both viable, the package SHALL present the trade-off explicitly.

#### Scenario: Globbing rule loses to narrower rules
- **WHEN** a broad affix and two narrow affixes both fix the focus, but the broad one over-generates on held-out forms
- **THEN** assessment ranks the narrow pair above the broad rule and surfaces the coverage-vs-overgeneration trade-off

#### Scenario: Archiphoneme collapse preferred when it round-trips
- **WHEN** an archiphoneme + phonological rule reproduces an allomorph family with no regressions
- **THEN** it is preferred over listing the allomorphs (fewer entries, no over-generation)

### Requirement: Decoy rejection on validation
Assessment SHALL reject decoy hypotheses (edits that fix the focus form but cause regressions) and accept
the true item, at a measured precision, on ablation validation scenarios.

#### Scenario: Decoy rejected, truth accepted
- **WHEN** a scenario offers the true affix and a broader decoy affix that over-generates
- **THEN** assessment accepts the true affix and rejects the decoy via the regression count
