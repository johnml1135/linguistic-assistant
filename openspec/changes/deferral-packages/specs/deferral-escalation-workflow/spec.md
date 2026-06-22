## ADDED Requirements

### Requirement: Automatic escalation trigger
The system SHALL escalate a ticket to the workflow fan-out only when it is auto-tagged `impact: high` or
sits in a dependency cluster of size ≥ K. Escalation routing SHALL be automatic from the tags; simple
low-impact tickets SHALL NOT incur the cost.

#### Scenario: High-impact ticket escalates
- **WHEN** a ticket's impact priority is high
- **THEN** it is routed to the escalation workflow

#### Scenario: Low-impact ticket does not escalate
- **WHEN** a ticket is low impact and unclustered
- **THEN** it is resolved with the Phase A/B package only, no workflow run

### Requirement: Parallel hypothesis investigation + synthesis
On escalation, the system SHALL fan out one hypothesis agent per relevant HC mechanism (each builds and
HC-tests its edit) and then synthesize a single enriched ticket (ranked hypotheses, the strongest
discriminating options, recomputed dependencies/impact). The synthesized ticket SHALL conform to the same
`DeferralTicket` schema.

#### Scenario: Fan-out produces one enriched ticket
- **WHEN** a ticket escalates
- **THEN** multiple mechanism agents run in parallel, each contributing HC-verified hypotheses, and a
  synthesizer emits one schema-valid ticket combining them

#### Scenario: Escalation is additive and verified
- **WHEN** the workflow proposes hypotheses
- **THEN** each is HC-verified (per counterfactual-parsing) before inclusion, and the deterministic
  hypotheses are retained
