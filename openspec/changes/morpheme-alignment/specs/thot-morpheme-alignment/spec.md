## ADDED Requirements

### Requirement: THOT aligns the source against the morpheme stream
The system SHALL align each verse's source tokens against the target **morpheme** stream (each target word
expanded to its morpheme forms as separate tokens) using the THOT HMM aligner, producing per morpheme the
set of aligned source tokens with each alignment probability.

#### Scenario: A morpheme receives its source link
- **WHEN** the morpheme stream is aligned against the source
- **THEN** each morpheme carries the source token(s) it aligned to and the alignment probability

#### Scenario: An affix aligns to its grammatical source word
- **WHEN** a target object-marker morpheme co-occurs with the source word "you" across the corpus
- **THEN** the aligner links that morpheme to "you" with a probability reflecting that co-occurrence

### Requirement: THOT is required — no silent fallback
The morpheme alignment SHALL call the aligner with the HMM backend and the co-occurrence fallback disabled,
so a missing `sil-machine[thot]` fails loudly. The co-occurrence backend SHALL be used only when a caller
explicitly requests it (offline tests), never as a silent degradation.

#### Scenario: Missing THOT fails loudly
- **WHEN** the HMM backend is requested but `sil-machine[thot]` is not installed
- **THEN** the run raises rather than silently degrading to co-occurrence

### Requirement: Portmanteau and null morphemes are allowed
The system SHALL allow a morpheme to align to several source tokens (a portmanteau morpheme) or to none (a
null / structural morpheme): it SHALL record the full set of aligned source tokens (possibly empty) with
their probabilities and SHALL NOT force a one-to-one morpheme↔source mapping.

#### Scenario: A null morpheme records no source link
- **WHEN** a purely structural morpheme aligns to nothing
- **THEN** its source-token set is empty and it is not assigned a spurious gloss

### Requirement: Deterministic given inputs
Given the same morpheme stream and corpus, the alignment SHALL produce the same per-morpheme links, and
each morpheme's links SHALL be traceable to it via the back-link.

#### Scenario: Repeated runs agree
- **WHEN** the alignment is run twice on the same inputs
- **THEN** the per-morpheme source links are identical
