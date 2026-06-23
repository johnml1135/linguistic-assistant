## ADDED Requirements

### Requirement: Detect each switch from the corpus with evidence
The system SHALL detect each catalog switch from the corpus, producing `value` (a contour), a `confidence`
in [0,1], and the concrete `evidence` (counts + examples) that supports it, reusing the existing pieces
(cycle affixes, `phonology_induce`, `morph_align_hc` markers, orthography, corpus statistics). A switch
whose evidence is unavailable SHALL be reported `unknown` (confidence 0), not guessed.

#### Scenario: A switch is detected with evidence
- **WHEN** detection runs for a pair
- **THEN** each switch yields a value + confidence + the supporting evidence (e.g. infixation: `-in-` ×154,
  N distinct stems, example `tatawag→tinatawag`)

#### Scenario: Missing evidence yields unknown
- **WHEN** the morpheme alignment needed for TAM/agreement has not been run
- **THEN** those switches report `unknown` (confidence 0), not a guess

### Requirement: Productivity gate against coincidental false positives
Detectors for processes (especially infixation and reduplication) SHALL apply a productivity test
(the Tolerance Principle, from `research/assess/`): a candidate process is reported `present` only if it
recurs across at least the tolerance threshold of **distinct stems**. A pattern found in too few distinct
stems SHALL NOT be reported present.

#### Scenario: Coincidental substring is rejected
- **WHEN** an internal chunk (e.g. swh `-ak-` from `lakini`) appears in too few distinct stems
- **THEN** infixation is not reported present on that evidence

#### Scenario: A productive affix is accepted
- **WHEN** an internal chunk (e.g. tgl `-in-`) appears across many distinct stems above the threshold
- **THEN** infixation is reported present with that evidence

### Requirement: Internet cross-check as a second opinion
Each detected value SHALL be compared to the WALS/Grambank seed (`profile._seed`): agreement SHALL raise
confidence and conflict SHALL be flagged on the result. The cross-check SHALL NOT silently override either
side — a detector can be wrong and the seed can be wrong/too-coarse.

#### Scenario: Agreement boosts, conflict flags
- **WHEN** detected `infixation=present` matches the seed for tgl
- **THEN** it is marked agreeing (higher confidence); **WHEN** detected conflicts with the seed (swh
  `lakini`), it is flagged conflicting for the human, not auto-resolved

### Requirement: Detection is deterministic and re-runnable
Given the same corpus and cached inputs, detection SHALL produce the same switch values/evidence, so a
result is reproducible and reviewable.

#### Scenario: Repeated detection agrees
- **WHEN** detection is run twice on the same inputs
- **THEN** the switch values and evidence are identical
