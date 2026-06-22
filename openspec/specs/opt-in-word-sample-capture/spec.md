# opt-in-word-sample-capture Specification

## Purpose
TBD - created by archiving change audio-evidence-addon. Update Purpose after archive.
## Requirements
### Requirement: Operators can declare opt-in sample words
The system SHALL accept an explicit sample-word manifest for the four targets (Swahili, Indonesian,
Tagalog, Spanish) that lets an operator nominate words to track through later enrichment. A sample
entry MUST support the target key, the chosen word form, and MAY include optional lemma, gloss,
reference, or analyst note fields.

#### Scenario: Sample manifest is accepted
- **WHEN** an operator supplies a valid sample-word manifest for one of `swh`, `ind`, `tgl`, or `spa`
- **THEN** the workflow loads the sample entries and preserves their declared metadata

#### Scenario: Sample manifest contains an unsupported target
- **WHEN** a sample-word manifest contains a target other than `swh`, `ind`, `tgl`, or `spa`
- **THEN** the workflow reports the invalid entry and does not treat it as accepted input

### Requirement: Sample words persist with resolution status
The workflow SHALL write a persisted sample-word dataset under the pair output and MUST record whether
each sample was resolved against the built pair data. Resolved entries MUST carry their matched text
anchors, and unresolved entries MUST remain present with an unresolved status.

#### Scenario: Sample word resolves to pair data
- **WHEN** a supplied sample word matches built pair data for the requested target
- **THEN** the persisted sample dataset records the matching reference or references for that word

#### Scenario: Sample word does not resolve
- **WHEN** a supplied sample word does not match the current built pair data
- **THEN** the persisted sample dataset keeps the sample entry and marks it unresolved

### Requirement: Sample words are prioritized during enrichment
When audio enrichment runs, the workflow SHALL prioritize persisted sample words for evidence and
report generation before broader optional analysis. Sample entries MUST remain in the output even when
no audio asset or no Allosaurus result is available for them.

#### Scenario: Sample word has no audio asset
- **WHEN** a prioritized sample word is present in the persisted sample dataset but has no local audio
  asset
- **THEN** the workflow keeps the sample in the output and records that audio was unavailable for it

#### Scenario: Sample word receives audio evidence
- **WHEN** a prioritized sample word has matching local audio and the Allosaurus add-on is available
- **THEN** the generated evidence and reports include that sample before non-prioritized items

