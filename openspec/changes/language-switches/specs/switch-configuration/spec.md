## ADDED Requirements

### Requirement: Confirmed switches are recorded in the language profile
The system SHALL record each switch decision in the per-language profile
(`golden_sets/<pair>/profile.json`) carrying `value`, `confidence`, `provenance`
(detected | internet | linguist), the supporting `evidence`, and a `locked` flag. The record SHALL
round-trip (write then reload losslessly).

#### Scenario: A confirmed switch is persisted with provenance
- **WHEN** a switch is confirmed (e.g. tgl infixation = present, by a linguist)
- **THEN** the profile stores value=present, provenance=linguist, locked=true, with the evidence, and it
  reloads identically

### Requirement: Every successive step reads the profile and is constrained by it
All later analysis (the hypothesis taxonomy, the segmenter, induction, the gold-raise) SHALL read the
profile and be constrained by the recorded switches. This is the load-bearing requirement: a switch
decision is not advisory.

#### Scenario: A recorded switch reaches the hypothesis space
- **WHEN** the taxonomy enumerates hypotheses for a pair
- **THEN** it consults the profile's switch-derived allowances (e.g. `allowed_affix_kinds`) rather than a default

### Requirement: A locked switch hard-prunes; an uncertain one is a soft prior
A `locked` switch SHALL be a hard constraint — a disallowed mechanism is never enumerated (e.g. no infix
hypothesis when infixation is locked absent; no gender feature when the language is noun-class). An
unconfirmed/low-confidence switch SHALL be a soft prior — deprioritized in ranking but still allowed and
probe-eligible.

#### Scenario: Locked-absent prunes the mechanism
- **WHEN** infixation is locked absent for Spanish and a no-parse hypothesis set is built
- **THEN** no infix hypothesis is enumerated

#### Scenario: Uncertain switch only deprioritizes
- **WHEN** reduplication is present-but-unconfirmed
- **THEN** reduplication hypotheses are ranked lower but not pruned, and remain probe-eligible

### Requirement: Switch decisions are falsifiable, not permanent
A recorded switch SHALL remain editable and probe-falsifiable: the "what if this were different" probe
(toggle + ΔMDL over the corpus) MAY recommend revisiting a switch, and a `locked` switch SHALL only be
changed by a human (the probe surfaces a recommendation, never auto-flips a locked switch).

#### Scenario: A probe recommends revisiting a locked switch
- **WHEN** toggling a locked switch materially improves the grammar (ΔMDL) with no regression
- **THEN** the system recommends the change to a human and does not auto-apply it
