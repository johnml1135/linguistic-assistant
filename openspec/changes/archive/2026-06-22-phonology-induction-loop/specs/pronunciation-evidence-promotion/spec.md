## ADDED Requirements

### Requirement: Pronunciation evidence is promoted only under human gate
The workflow SHALL promote pronunciation evidence to `lexical.pronunciation.create` change-set ops only
after explicit human confirmation, recording rationale, confidence, provenance, and the target writing
system on the op. It MUST NOT emit pronunciation ops automatically from phone evidence.

#### Scenario: Analyst confirms a pronunciation candidate
- **WHEN** an analyst confirms a pronunciation candidate derived from phone evidence
- **THEN** the workflow emits a `lexical.pronunciation.create` op carrying its form, writing system,
  rationale, confidence, and provenance

#### Scenario: Candidate is not confirmed
- **WHEN** a pronunciation candidate is not confirmed by an analyst
- **THEN** it remains review-only evidence and no change-set op is emitted

### Requirement: Generated surface vs recorded pronunciation is a consistency check
The workflow SHALL surface any disagreement between a Hermit-Crab-generated surface form and a recorded
pronunciation for an entry as a consistency check pointing at the phoneme inventory or phonological
rules. This MUST be a reviewable signal, never an automatic edit.

#### Scenario: Generated surface disagrees with recorded pronunciation
- **WHEN** the generated surface form and the recorded pronunciation for an entry differ
- **THEN** the workflow flags a consistency check and makes no automatic change to the grammar or lexicon
