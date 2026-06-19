## ADDED Requirements

### Requirement: Candidate localization is optional and sample-driven
The system SHALL provide an explicit workflow that searches eligible local audio assets for persisted
sample words and records candidate occurrences without mutating the lexicon or any database. The
workflow MUST restrict itself to supported targets and MUST complete with status output when no
searchable backend, no eligible local audio, or no resolved sample words are available.

#### Scenario: Candidate localization runs for a resolved sample word
- **WHEN** an operator runs candidate localization for one of `swh`, `ind`, `tgl`, or `spa` with a resolved sample word and
  at least one eligible local audio asset whose anchor covers that sample's reference
- **THEN** the workflow searches that asset and persists one or more candidate occurrences for review

#### Scenario: Search backend is unavailable
- **WHEN** an operator runs candidate localization but the configured word-timestamp backend is not
  installed or cannot be initialized
- **THEN** the workflow completes without candidate results and records the backend as unavailable

### Requirement: Candidate records persist location, ranking, and provenance
Each persisted candidate occurrence SHALL include a stable identifier, sample word, matched token,
source audio path, source identifier, anchor provenance, start and end offsets, preview defaults,
backend provenance, total score, and score breakdown. The workflow MUST store candidates in a
reviewable artifact under the pair directory and MUST preserve multiple ranked candidates for the same
sample word when more than one match is found.

#### Scenario: Multiple candidates are persisted for one sample word
- **WHEN** the search backend returns more than one matching occurrence for a sample word
- **THEN** the persisted artifact stores all candidates in descending rank order with stable IDs and
  per-candidate score breakdowns

#### Scenario: Candidate artifact is written
- **WHEN** candidate localization finishes for a pair directory
- **THEN** the workflow writes a plain-file occurrence artifact under that pair's `audio/` folder with
  source, offset, and provenance metadata for each candidate

### Requirement: Candidate ranking is conservative and phonology-oriented
The workflow SHALL rank candidates using transparent review-oriented signals that include lexical match
quality, backend confidence, boundary quality, and optional phonology cues. Exact normalized matches
MUST outrank stem-aware-only matches when other evidence is comparable. Optional phone evidence or
feature mapping MUST remain review-only and MUST NOT be treated as parser-authoritative.

#### Scenario: Exact match outranks stem-aware match
- **WHEN** one candidate is an exact normalized match for the sample word and another candidate is only
  a stem-aware match with otherwise similar evidence
- **THEN** the exact normalized match receives the higher rank

#### Scenario: Phonology cues are absent
- **WHEN** candidate localization cannot produce phone evidence for a stored occurrence
- **THEN** the candidate remains persisted with lexical and timing evidence only rather than being
  discarded

### Requirement: Candidate artifacts include context helpful for phonology review
Each stored candidate SHALL include the surrounding recognized word context and any available
review-only phone or feature cues needed to compare likely pronunciations or harmony-relevant vowels.

#### Scenario: Candidate has review-only phone cues
- **WHEN** the workflow can derive phone evidence for a candidate occurrence
- **THEN** the stored candidate includes the observed phones and any mapped vowel-feature summary as
  review-only metadata

#### Scenario: Candidate has transcript context only
- **WHEN** the workflow stores a candidate occurrence without phone evidence
- **THEN** the stored candidate still includes surrounding word context for analyst review