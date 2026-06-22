## ADDED Requirements

### Requirement: Two-signal auto-accept at ≥99.5% precision
The system SHALL auto-accept a proposal without human review only when two independent signals concur —
the THOT aligner's top candidate and a light LLM high-confidence check agree — and SHALL be calibrated so
the accepted set holds at least the **per-language precision bar** read from the language profile
(default **≥99.5%**, e.g. **99.9%** for a stricter language; see `language-profile`) against the gold.
Auto-accept SHALL be limited to lexical glosses/POS; it SHALL NOT auto-accept morphology or phonology.

#### Scenario: Both signals agree → auto-accept
- **WHEN** THOT's top gloss and the LLM's high-confidence gloss for a word agree
- **THEN** the proposal is auto-accepted and applied without a ticket

#### Scenario: Signals disagree → defer, not accept
- **WHEN** the two signals disagree or the LLM is not high-confidence
- **THEN** the item is NOT auto-accepted; it falls through to the ticket pipeline (stages 2–4)

### Requirement: Auto-accepted items are flagged and auditable
Every auto-accepted item SHALL be tagged `source: ai-auto` and recorded with its two signals, so it can be
audited, re-reviewed, and reverted if later shown to be wrong.

#### Scenario: Audit and revert
- **WHEN** an auto-accepted gloss is later found to be wrong
- **THEN** the record identifies it as `ai-auto` with its evidence and supports reverting it from the gold

### Requirement: Precision is measured, not assumed
The system SHALL report the auto-accept precision against the gold on the validation set, and SHALL surface
a regression if a change drops it below that pair's per-language bar (from the profile).

#### Scenario: Precision regression is caught
- **WHEN** a pipeline change lowers auto-accept precision below the pair's profile bar on the validation set
- **THEN** the validation run flags it as a regression
