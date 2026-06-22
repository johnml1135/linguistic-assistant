# phonology-aware-grammar-induction Specification

## Purpose
TBD - created by archiving change phonology-induction-loop. Update Purpose after archive.
## Requirements
### Requirement: The grammar scaffold supports phonological natural classes
The induction scaffold SHALL be able to express vowel and consonant natural classes (e.g. front/back,
±round) rather than only per-character symbols, so that a single archiphoneme affix plus one
phonological rule over a class can be generated and parsed by Hermit Crab.

#### Scenario: A harmony family is expressible as one rule
- **WHEN** the cycle holds two or more affixes that share a consonant skeleton and differ only in
  harmony vowels (e.g. `lar`/`ler`)
- **THEN** it can construct one archiphoneme affix plus a rule over the conditioning natural class that
  generates both surface forms

#### Scenario: Natural classes are absent
- **WHEN** no natural classes are defined for a target
- **THEN** induction still runs in the prior per-affix mode without error

### Requirement: Allomorph collapse is accepted only on the coverage gate
When the cycle proposes collapsing an allomorph set into one archiphoneme affix plus a rule, it SHALL
keep the change only if Hermit Crab coverage on the held-out forms does not fall AND the affix count
strictly decreases. Otherwise it MUST revert and retain the listed allomorphs.

#### Scenario: Collapse is accepted
- **WHEN** the collapsed archiphoneme affix plus rule reparses the held-out forms with coverage held and
  fewer total affixes
- **THEN** the cycle keeps the rule, removes the redundant allomorphs, and records the reduced
  `enumeration_debt`

#### Scenario: Collapse is rejected
- **WHEN** the collapsed form drops coverage or fails to reduce the affix count
- **THEN** the cycle reverts the change and keeps the previously accepted allomorphs

### Requirement: Enumeration debt is reported as the optimization target
The cycle SHALL report `enumeration_debt` and its change across iterations so that progress is measured
as debt paid down, not only as coverage gained.

#### Scenario: Debt decreases after a successful collapse
- **WHEN** a collapse is accepted
- **THEN** the reported `enumeration_debt` for the run is lower than before the collapse

### Requirement: Observed phones may act as a second, independent generation gate
The cycle SHALL support comparing the Hermit-Crab-generated surface form against observed phone evidence
as an additional, independent gate when such evidence exists. A mismatch MUST be surfaced as a reviewable
flag and MUST NOT automatically alter the grammar, lexicon, or phoneme features.

#### Scenario: Generated surface conflicts with observed phones
- **WHEN** a generated surface form disagrees with the observed phone evidence for that form
- **THEN** the workflow records a consistency flag and makes no automatic grammar or feature change

#### Scenario: No phone evidence is available
- **WHEN** no phone evidence exists for the forms under test
- **THEN** induction proceeds on the text coverage gate alone

