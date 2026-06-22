## ADDED Requirements

### Requirement: Hypotheses auto-enumerated from the HC-mechanism taxonomy
The system SHALL enumerate hypotheses from a fixed taxonomy keyed by the deferral `type`, mapping each type
to the applicable HC resolution mechanisms (e.g. no-parse → {add LexEntry root, add MoStemAllomorph of the
nearest lemma, stem + known affix, add PhonologicalRule, **infix rule**, **archiphoneme-collapse of an
allomorph family**}; homograph → {split into senses/POS}; unknown affix → {MoInflAffMsa with candidate
function, tagged inflectional vs derivational}). This enumeration SHALL require no LLM.

#### Scenario: No-parse word yields the standard hypothesis set
- **WHEN** a no-parse deferral is built
- **THEN** the ticket contains the taxonomy's hypotheses for that type, each a typed grammar edit

#### Scenario: Allomorph family yields a collapse hypothesis
- **WHEN** several affix allomorphs share a function and differ by a phonologically-conditioned segment
- **THEN** the taxonomy includes an archiphoneme-collapse hypothesis (one underlying form + a rule) alongside
  the list-the-allomorphs hypothesis

### Requirement: Taxonomy enumeration is filtered by the language profile
The taxonomy SHALL consult the pair's language profile (see `language-profile`) before enumerating: a
hypothesis whose mechanism is locked-off for the language (e.g. an infix for a non-infixing language, a
gender feature for a noun-class language) SHALL NOT be produced, and uncertain-feature mechanisms SHALL be
emitted but flagged as soft-disfavored for ranking. This pruning is deterministic and LLM-free.

#### Scenario: Disallowed mechanism is pruned from the hypothesis set
- **WHEN** a no-parse deferral is built for a language whose profile locks infixation = false
- **THEN** the enumerated hypotheses exclude any infix edit and include only the profile-allowed mechanisms

### Requirement: Repair hypotheses for a noisy grammar
Because the grammar may contain wrong rules, the taxonomy SHALL include repair hypotheses — **narrow/condition**
an existing rule, **retract** a rule, or **split** an over-broad entry — not only additions. A rule implicated
in many mis-parses or in other hypotheses' regressions SHALL be eligible to become its own ticket.

#### Scenario: An over-broad rule is proposed for narrowing/retraction
- **WHEN** an existing affix rule is implicated in widespread mis-parses
- **THEN** the ticket includes hypotheses to narrow or retract that rule, with their counterfactual effect

### Requirement: Intelligible presentation with discriminating edge cases
The package SHALL present concrete reparse consequences ("if A, this verse parses as X; if B, as Y") and
SHALL select the **edge cases that best discriminate the live hypotheses** — the forms the candidate
hypotheses parse differently — rather than arbitrary examples.

#### Scenario: Discriminating example chosen
- **WHEN** hypotheses A and B agree on most forms but differ on one
- **THEN** that distinguishing form is shown to the reviewer with both reparses and the "is X correct?" prompt

### Requirement: Presentation options from the question catalog
The system SHALL select 5–10 presentation options from `parsegym/questions.py`, choosing archetypes
appropriate to the type and hypotheses (e.g. `meaning_choice` for a homograph, `minimal_pair` /
`allomorph_check` for a lexeme-vs-affix split, `paradigm_fill` for a missing form) and slot-filling each
from the ticket's target and candidates.

#### Scenario: Options are rendered and mapped to hypotheses
- **WHEN** options are built for a ticket with hypotheses A and B
- **THEN** at least 5 options are produced, each rendered with the target filled in and tagged with the
  hypotheses it discriminates

### Requirement: Automatic impact and dependency computation
The system SHALL compute `impact` (corpus frequency × the number of wordforms a resolution would newly
parse/gloss) and `dependencies` (shared lemma/affix/stem with other open tickets) from the corpus and the
gold, with no LLM.

#### Scenario: Impact reflects corpus frequency
- **WHEN** a high-frequency affix is ticketed
- **THEN** its `impact` priority is higher than a hapax lexeme ticket

### Requirement: LLM-free completeness
The deterministic builder SHALL produce a complete, valid ticket (hypotheses, counterfactuals, ≥5 options,
tags, a templated `context_md`) with no model endpoint available.

#### Scenario: Offline build
- **WHEN** the builder runs with no LLM endpoint configured
- **THEN** it still emits a schema-valid ticket with HC counterfactuals and templated prose

### Requirement: Backfill CLI from existing defer records
The system SHALL provide a CLI that converts existing `defer` records (from `propose.py` / sense-pick /
affix outputs) into tickets in the store.

#### Scenario: Backfill the current deferrals
- **WHEN** the backfill CLI is run for a pair with existing `defer` records
- **THEN** a ticket is created per deferral and written to the store
