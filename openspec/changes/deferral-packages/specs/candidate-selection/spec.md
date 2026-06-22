## ADDED Requirements

### Requirement: Deterministic next-candidate selection
Given a grammar state and the set of currently non-parsing (or deferred) forms, the system SHALL
deterministically rank the next-most-resolvable targets to attack, combining the THOT alignment signal with
corpus algorithms (impact = frequency × forms affected; resolvability = closeness to a known lemma/affix;
clustering). This SHALL require no LLM.

#### Scenario: Highest-impact resolvable target first
- **WHEN** selection runs over a state with many failing forms
- **THEN** a frequent form near a known lemma ranks above a rare, isolated one

### Requirement: Cluster surface forms that likely share one lexeme
The system SHALL detect groups of distinct surface forms that map (via THOT) to the same translation word
and are orthographically close, and SHALL propose them as a single candidate ("these forms are likely one
lexeme/paradigm").

#### Scenario: Forms→one-lexeme clustering
- **WHEN** four surface forms all align to the same English word and share a stem
- **THEN** they are surfaced as one candidate group, not four separate targets

### Requirement: Worst-part ranking drives selection
The system SHALL use `research/assess/worst_part.py`'s per-construct ablation ranking ("what's the worst
part of this grammar?") as a primary input to candidate selection — attacking the construct whose removal
most improves the grammar (highest MDL/coverage payoff), which is also the prime suspect for a wrong rule.

#### Scenario: Worst construct is selected next
- **WHEN** the worst-part ranking flags an over-generating affix as the costliest construct
- **THEN** candidate selection surfaces it as a top target (to repair/narrow), not just unparsed words

### Requirement: Selection recall on ablation scenarios
On ablation validation scenarios, selection SHALL surface the ablated region (the forms broken by the
removed item) among its top-ranked candidates at a measured recall.

#### Scenario: Ablated region is selected
- **WHEN** a known affix is ablated and many forms break
- **THEN** selection surfaces that affix's broken forms as a top candidate
