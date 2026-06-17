## ADDED Requirements

### Requirement: Case input contract
The harness SHALL accept a **Case** — raw interlinear data plus an *incomplete* lexicon and grammar —
through a single typed shape, and SHALL be agnostic to whether the case has a hidden answer key
(golden) or not (real). The Case SHALL be loadable from the golden on-disk layout
(`research/golden/<glottocode>/`: `raw/igt.jsonl`, an ablated `gold/lexicon.lift`,
`gold/grammar.hcgr.xml`) and from a real-case adapter that supplies the same fields.

#### Scenario: Load a golden instance as a Case
- **WHEN** the runner reads a golden instance directory produced by the sibling ablator
- **THEN** the harness yields a `Case` with the raw IGT, the incomplete lexicon, and the incomplete
  grammar populated, and with any answer key kept out of the `Case` object the model sees

#### Scenario: Real case uses the identical shape
- **WHEN** a real (no-answer-key) FLEx-derived case is supplied through the adapter
- **THEN** `propose()` accepts it unchanged and returns a change-set, with no golden-only fields required

### Requirement: Deterministic context assembly
The harness SHALL assemble the model context as a compiled language **primer** plus
**harness-orchestrated retrieval** of case-relevant facts (entries, paradigms, parallel evidence)
selected in code. It SHALL NOT rely on model-issued tool calls and SHALL NOT use vector/embedding
retrieval. Given identical inputs and config, the assembled context SHALL be byte-identical across
runs and across the Python and (future) C# implementations.

#### Scenario: Same inputs produce identical context
- **WHEN** context is assembled twice for the same Case with the same config
- **THEN** the two rendered context strings are byte-identical

#### Scenario: Retrieval is code-driven
- **WHEN** the harness needs case-relevant lexicon/grammar facts
- **THEN** it selects them with deterministic queries over the case's data and injects them after the
  primer, without asking the model to choose what to retrieve

### Requirement: Constrained, validated change-set output
The harness SHALL request output constrained to the change-set schema (GBNF/grammar where the backend
supports it; JSON schema otherwise) and SHALL validate every returned operation against the change-set
schema before use. Output that fails validation SHALL be rejected and recorded as a failed proposal —
never silently applied or coerced.

#### Scenario: Constrained decoding requested per backend
- **WHEN** the backend is an ik_llama/openai_compat endpoint
- **THEN** a `grammar` (GBNF) constraint is sent; **WHEN** the backend is the Anthropic/BYOK path,
  a `json_schema` constraint is sent

#### Scenario: Invalid proposal is rejected, not applied
- **WHEN** the model returns text that does not validate against the change-set schema
- **THEN** the harness records a validation failure for that case and emits no change-set ops for it

### Requirement: Swappable backend with direct local control
The harness SHALL select the model backend by configuration (default local `ik_llama`; `opus`/BYOK
when chosen) using the existing `LLMClient` interface, with no code change to swap. For the local
path it SHALL pass direct-control fields (`cache_prompt`, `grammar`, `seed`, `n_keep`) through the
`openai_compat` kwargs seam.

#### Scenario: Default to local, switch to BYOK by config
- **WHEN** no endpoint is specified
- **THEN** the harness uses the `ik_llama` local endpoint; **WHEN** `opus` is selected and a key is
  present, the same `propose()` call runs against the BYOK backend

### Requirement: Reproducible proposals
For a deterministic backend (greedy, fixed seed) the harness SHALL produce the same change-set for the
same Case across runs, so eval scores and RL rewards are reproducible.

#### Scenario: Greedy run is repeatable
- **WHEN** `propose()` runs twice on the same Case against the same model at temperature 0 with a fixed seed
- **THEN** the two change-sets are identical
