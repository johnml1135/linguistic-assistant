## ADDED Requirements

### Requirement: Ablation-generated ground-truth scenarios
The system SHALL generate validation scenarios by removing a known item from the verified gold grammar (a
LexEntry / MoStemAllomorph / MoInflAffMsa / PhonologicalRule), re-parsing to find the forms that break, and
recording `(ablated grammar state, broken focus forms, ground_truth = removed item, type, impact)`. It
SHALL produce hundreds of such scenarios across the four languages.

#### Scenario: Ablating an affix yields a scenario with a known answer
- **WHEN** a known affix rule is removed from the gold grammar
- **THEN** a scenario is emitted listing the now-failing forms with the removed rule as ground truth

#### Scenario: Scenarios span types and impact
- **WHEN** the generator runs
- **THEN** scenarios cover lexeme/affix/phonology/homograph types and are tagged high/low impact

### Requirement: Decoy hypotheses for regression testing
Scenarios SHALL include decoy hypotheses — edits that fix the focus form but cause regressions — so
stage-4 assessment can be measured on rejecting damaging fixes.

#### Scenario: A scenario carries a regressing decoy
- **WHEN** a scenario is generated for an ablated affix
- **THEN** it includes at least one decoy edit that parses the focus but breaks other forms

### Requirement: Per-stage scoring harness
The system SHALL score each pipeline stage on the validation set with its own metric: stage 1 precision
(≥99.5% target), stage 2 candidate recall, stage 3 hypothesis recall (does the true fix appear?), stage 4
assessment precision + regression-catch rate. The harness SHALL report per-stage and end-to-end numbers.

#### Scenario: A change is scored per stage
- **WHEN** the harness runs after a pipeline change
- **THEN** it reports stage-1 precision, stage-2/3 recall, stage-4 precision + regression-catch, and the
  end-to-end auto-resolution rate, flagging any metric that regressed

### Requirement: Complementary defer scenarios
The validation set SHALL also include scenarios whose correct outcome is to DEFER (no confident fix
exists), reusing/extending the ParseGym `ask_speaker` / `unknown` cases, so the pipeline is scored on
correctly *not* acting as well as on acting.

#### Scenario: Genuinely ambiguous case is deferred
- **WHEN** a scenario has no resolvable hypothesis from the corpus
- **THEN** the correct scored outcome is a deferral to the user, not a confident auto-resolution
