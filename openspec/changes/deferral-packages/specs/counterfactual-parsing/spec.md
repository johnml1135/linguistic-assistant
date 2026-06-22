## ADDED Requirements

### Requirement: A hypothesis is a typed grammar edit
The system SHALL represent each hypothesis as a typed edit over the gold `LangModel`: add LexEntry, add
MoStemAllomorph, add MoInflAffMsa (affix rule), add PhonologicalRule, split homograph, or re-segment. The
edit SHALL be applyable to a clone of the gold grammar without mutating the gold.

#### Scenario: Edit applies to a grammar clone
- **WHEN** a hypothesis edit is applied
- **THEN** a new `LangModel` reflecting the edit is produced and the gold grammar is unchanged

### Requirement: Counterfactual re-parse and diff (deterministic)
For each hypothesis, the system SHALL run the HC parser (`golden/hc.py`) on the focus verse plus 3–5
related verses and record, per verse, the current parse and the parse under the hypothesis, as a diff
("now" vs "if-hypothesis"). This step SHALL require no LLM.

#### Scenario: Hypothesis changes the focus parse
- **WHEN** the focus form does not parse and hypothesis A adds the allomorph that lets it parse
- **THEN** the ticket shows `now: no parse` and `if_A: <lemma + analysis>` for the focus verse

#### Scenario: Related verses show consequences
- **WHEN** a hypothesis is evaluated
- **THEN** the diff includes 3–5 related verses so the reviewer sees the broader effect of accepting it

### Requirement: Related-verse selection
The system SHALL select related verses by shared root/affix/stem and corpus frequency, deterministically,
so the same ticket yields the same evidence set.

#### Scenario: Deterministic evidence set
- **WHEN** counterfactuals are built twice for the same ticket
- **THEN** the same related verses are chosen

### Requirement: Bounded, honest verification
Counterfactual parsing SHALL be chunked with a per-verse timeout; a hypothesis whose parse times out SHALL
be marked `unverified` rather than presented as confirmed.

#### Scenario: Timeout is marked, not hidden
- **WHEN** HC search times out on a hypothesis grammar
- **THEN** that hypothesis is flagged `unverified` in the ticket and is not ranked as a confirmed option
