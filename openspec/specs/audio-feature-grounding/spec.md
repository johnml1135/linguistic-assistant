# audio-feature-grounding Specification

## Purpose
TBD - created by archiving change phonology-induction-loop. Update Purpose after archive.
## Requirements
### Requirement: Phone evidence is mapped to features to confirm conditioning
When phone evidence exists for words in a harmony family, the workflow SHALL derive a review-only
phonetic-feature mapping and use it to confirm or refute the family's hypothesized conditioning feature
(e.g. backness, rounding). The mapping MUST be recorded as a hypothesis with provenance and MUST NOT be
treated as an authoritative phonemic claim or a Hermit Crab feature edit.

#### Scenario: Audio confirms the conditioning feature
- **WHEN** phone evidence for a family's members aligns with the hypothesized conditioning feature
- **THEN** the workflow records a confirmation with the supporting phones and provenance

#### Scenario: Audio conflicts with the conditioning feature
- **WHEN** phone evidence for a family's members contradicts the hypothesized conditioning feature
- **THEN** the workflow records a reviewable conflict and does not alter the grammar or features

### Requirement: Sample words resolve through induced stems
Sample-word resolution SHALL match a word against its inflected occurrences by resolving through the
cycle's induced stems, not only by exact surface match, while preserving the existing
matched/unresolved persistence contract.

#### Scenario: An inflected occurrence is matched via its stem
- **WHEN** a sample word's stem is an induced root and an inflected form of it appears in the pair data
- **THEN** the resolved sample records the matching reference(s) for that inflected occurrence

### Requirement: Triangulation combines available witnesses and degrades gracefully
The workflow SHALL produce a triangulation summary that combines orthography, distributional evidence
(harmony families), and — when present — phone evidence. It MUST produce a useful summary when no audio
is available, using orthography and distribution alone.

#### Scenario: Triangulation with no audio
- **WHEN** the workflow runs with text and distributional evidence but no phone evidence
- **THEN** it still emits a triangulation summary marking the audio witness as absent

#### Scenario: Triangulation with all three witnesses
- **WHEN** orthography, distribution, and phone evidence are all present for a word
- **THEN** the summary reports their agreement or flags their disagreement

