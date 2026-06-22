## ADDED Requirements

### Requirement: Audio enrichment is optional and scope-limited
The system SHALL provide audio enrichment only as an explicit add-on over existing pair data for the
four targets (Swahili, Indonesian, Tagalog, Spanish). It MUST NOT run implicitly during the base text
build, and it MUST complete with status output rather than fail when no local audio assets or no
Allosaurus runtime are available.

#### Scenario: No local audio is available
- **WHEN** an operator runs audio enrichment for one of `swh`, `ind`, `tgl`, or `spa` and the catalog
  has no local audio asset for the requested unit
- **THEN** the workflow completes successfully and records that audio was unavailable for that unit

#### Scenario: Unsupported target is requested
- **WHEN** an operator runs audio enrichment for a target other than `swh`, `ind`, `tgl`, or `spa`
- **THEN** the workflow rejects the request with a clear scope error

### Requirement: Raw phone evidence is provenance-bearing and non-authoritative
When local audio and Allosaurus are available, the system SHALL produce raw phone evidence records that
include the target pair, source audio asset, text anchor, runtime provenance, and the recognized phone
output. If timestamps are requested, the record MUST include them. The workflow MUST NOT treat these
records as direct Hermit Crab phoneme or feature assertions.

#### Scenario: Audio evidence is generated with timestamps
- **WHEN** an operator runs the add-on on a locally available audio asset with timestamp output enabled
- **THEN** the resulting evidence record includes raw phones, timestamp data, and the Allosaurus
  runtime provenance used to produce them

#### Scenario: Audio evidence conflicts with existing text expectations
- **WHEN** the add-on observes phone evidence that does not align with the current orthographic
  expectation
- **THEN** the workflow records reviewable evidence and does not emit a parser or phoneme mutation

### Requirement: Enrichment reports are derived and review-only
The workflow SHALL derive pronunciation candidates, orthography or misspelling alerts, and
triangulation summaries from pair data plus optional phone evidence. These outputs MUST be stored as
derived artifacts and MUST NOT create an `audio/*` change-set tier or an audio-driven parser input
path.

#### Scenario: Misspelling alert is emitted
- **WHEN** the workflow finds a reviewable mismatch between repeated text forms and available phone
  evidence
- **THEN** it emits an orthography or misspelling alert with the evidence that triggered the alert

#### Scenario: No phone evidence exists
- **WHEN** the workflow runs only with text data and sample-word selections
- **THEN** it still produces derived status artifacts without claiming pronunciation evidence