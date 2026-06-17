## Why

We need to know whether a local **30B-class model** (Gemma 4 / Qwen 3.6 via ik_llama) — or a
**BYOK frontier** model — can propose lexicon and morphophonology edits *well enough* on **held-out
languages**, measured against the golden set a sibling agent is building. The decisive design bet is
that the pipeline which **scores a model on golden (known-answer) instances is the exact same pipeline
that proposes edits on real (unknown-answer) FLEx projects** — golden cases are just real cases with
an answer key. Building that one pipeline now, Python-only, lets us iterate the model/skill against
the golden set and graduate the *same code* to production.

## What Changes

- Add a **proposal harness** (`research/proposal/`): given a *case* (raw IGT + an incomplete
  lexicon/grammar), deterministically assemble context (compiled language **primer** +
  **harness-orchestrated** retrieval — no model-driven tool calls, no vector search), call the
  swappable backend with **grammar/schema-constrained** decoding, and parse a validated **change-set**
  of LIFT + Hermit Crab edit operations. This core is identical for golden and real cases.
- Add a **golden eval runner** (`research/eval/`): iterate golden instances, invoke the proposal
  harness, hand the proposal to the golden **scorer**, and emit per-instance + summary JSONL mirroring
  `research/benchmarks/results/`.
- Define the **case/proposal/score contract** (typed) so this harness and the sibling golden-set work
  interoperate without stepping on each other: a `Case`/`Instance` shape (consumes
  `research/golden/<glottocode>/…`), a `ChangeSet` proposal shape (LIFT/HC ops), and a `Scorer`
  protocol (the deterministic `(instance, proposal) → reward` from the golden-set design).
- Extend the existing `LLMClient` path for **direct local control**: pass `cache_prompt`, `grammar`
  (GBNF), `seed`, `n_keep` through the `openai_compat` kwargs seam; use `json_schema` for the
  Anthropic/BYOK path. No new client SDKs.
- Provide a **mock backend + tiny fixture instance** so the whole loop runs deterministically with no
  model and no network (CI-able while real golden data lands).

## Capabilities

### New Capabilities
- `proposal-harness`: turn a case (raw data + incomplete lexicon/grammar) into a validated LIFT/HC
  change-set via deterministic context assembly, constrained decoding, and a swappable backend — the
  shared core reused unchanged for golden eval and real proposals.
- `golden-eval-runner`: run the proposal harness across golden instances, score each via the golden
  scorer, and produce reproducible results — the eval/RL wrapper around the shared core.

### Modified Capabilities
<!-- None — no existing OpenSpec specs define these behaviors yet. -->

## Impact

- **New code:** `research/proposal/` (context assembly, constrained-output, change-set parse/validate),
  `research/eval/` (runner, reporting), shared contract types.
- **Reuses:** `research/harness/` (`base.LLMClient`, `openai_compat`, `anthropic_client`, `config`,
  `mock`); `research/golden/` (instances, ablator, scorer — owned by the sibling agent, consumed via
  the contract); `serving/` ik_llama; `linguistics/` primitives/skills for the primer/prompt content.
- **Contract dependency:** the golden-set on-disk layout and `Scorer` interface from
  `docs/superpowers/specs/2026-06-16-golden-set-design.md` — coordinated with the sibling agent.
- **Out of scope:** C# port, real `.fwdata` ingestion, parallel-translation-QA gold, RL training loop
  (the scorer is designed as a pure reward fn so RL can attach later).
