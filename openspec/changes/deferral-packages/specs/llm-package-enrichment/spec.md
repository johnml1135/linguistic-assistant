## ADDED Requirements

### Requirement: LLM adds hypotheses beyond the taxonomy
The system SHALL offer an optional enrichment pass (a `package_builder` skill via the swappable `harness/`
client) that proposes hypotheses the deterministic taxonomy does not cover (e.g. suppletion, an irregular
split), each expressed as a typed grammar edit. Enrichment SHALL be strictly additive to the Phase A ticket.

#### Scenario: Out-of-taxonomy hypothesis is added
- **WHEN** the model proposes a suppletive-stem hypothesis the taxonomy missed
- **THEN** it is added to the ticket's hypotheses without removing the deterministic ones

### Requirement: Every model hypothesis is HC-verified before inclusion
Each LLM-proposed hypothesis SHALL be run through the counterfactual engine; a hypothesis whose edit does
not let the focus form parse (or times out) SHALL be dropped or marked `unverified` — the LLM SHALL NOT
inject an unparsed claim as confirmed.

#### Scenario: Unparseable model hypothesis is rejected
- **WHEN** a model hypothesis does not parse the focus form under HC
- **THEN** it is excluded from the ticket's confirmed hypotheses

### Requirement: LLM writes the human narrative and selects discriminating options
The system SHALL let the model write the `context_md` narrative ("where I started / what I'm focusing on /
the options") and choose/phrase the most discriminating presentation options. This prose SHALL be
non-authoritative: the JSON hypotheses and HC counterfactuals remain the source of truth.

#### Scenario: Prose is non-authoritative
- **WHEN** the model's narrative disagrees with the HC counterfactual
- **THEN** the HC counterfactual is what the ticket records as fact; the prose is clearly model-authored

### Requirement: Endpoint-swappable and offline-degradable
Enrichment SHALL run against any harness endpoint (Gemma via ik_llama, Opus, mock) and, when no live
endpoint is configured, SHALL be skipped without failing the ticket build.

#### Scenario: No endpoint
- **WHEN** enrichment is requested but no endpoint is reachable
- **THEN** the Phase A ticket is emitted unchanged and the skip is reported
