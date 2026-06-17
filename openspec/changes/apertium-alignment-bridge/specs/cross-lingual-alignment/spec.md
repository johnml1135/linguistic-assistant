## ADDED Requirements

### Requirement: Bilingual sense-link tier
The system SHALL store cross-lingual **sense links** (vernacular sense ↔ reference-language lemma/sense)
as a reviewable `bilingual/*` change-set tier, each op carrying rationale, confidence, and provenance —
the authoritative source from which Apertium bidix artifacts are derived. Sense links SHALL be the
primary store; Apertium `.dix` files SHALL be treated as derived build artifacts, never hand-edited.

#### Scenario: Add a reviewed sense link
- **WHEN** a vernacular sense is linked to a reference-language lemma
- **THEN** a `bilingual.sense_link.add` op is emitted with both endpoints, rationale, confidence, and
  provenance, reviewable as plain text alongside `lexical/*` ops

#### Scenario: Bidix is regenerated, not edited
- **WHEN** the sense-link tier changes
- **THEN** the Apertium bidix is regenerated from it; a hand-edited bidix is never the source of truth

### Requirement: Deterministic morphology-aware reference finder
The system SHALL locate a source concept's realization in a target sentence using lemma-level matching:
source lemma → bidix → candidate vernacular lemma(s) → match against the target tokens' Hermit Crab
lemma analyses. Matching SHALL be on **lemma + tags**, not surface form, so it survives word-order
differences and inflection. The finder SHALL be deterministic (same inputs → same result) and SHALL NOT
use Constraint Grammar or any statistical/stochastic aligner in the core path.

#### Scenario: Find a reference under reordering and inflection
- **WHEN** a source lemma maps via bidix to a vernacular lemma whose inflected form appears anywhere in
  a reordered target sentence
- **THEN** the finder returns the matching target token(s) with their HC analysis (lemma + features),
  regardless of position or surface inflection

#### Scenario: Missing concept is reported, not guessed
- **WHEN** no target token's HC lemma matches any bidix candidate for the source lemma
- **THEN** the finder reports the concept as unrealized (a candidate "missing concept" flag), without
  inventing an alignment

### Requirement: Feeds parallel-translation QA flags
The reference finder SHALL supply the alignment substrate for `parallel-translation-qa`, enabling its
missing-concept, wrong-sense, and agreement/feature-mismatch checks on imperfectly-aligned sentences.
It SHALL emit located source↔target correspondences with confidence; it SHALL NOT generate target text.

#### Scenario: Agreement check uses the located token
- **WHEN** a source concept is located in the target via the finder
- **THEN** the target token's HC features are compared to the source backbone and a feature-mismatch
  flag is raised on disagreement (e.g. singular source, plural target) for human review — never auto-applied

### Requirement: Determinism is verifiable offline
The reference finder SHALL run without the Apertium binary when given an in-repo bidix and HC analyses
(or recorded fixtures), so its determinism is testable in CI with no native dependency and no network.

#### Scenario: Fixture run is reproducible
- **WHEN** the finder runs twice over the same fixture (bidix + analyzed source/target)
- **THEN** it returns identical correspondences and flags both times
