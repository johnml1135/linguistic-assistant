## Context

The golden-set design (`docs/superpowers/specs/2026-06-16-golden-set-design.md`) defines verified
per-language lexicon+grammar, an **ablator** that removes pieces to make an instance, and a
**scorer** that applies a proposed change-set, runs Hermit Crab, and returns a reward gated on
non-regression. A sibling agent is building that under `research/golden/` *now*. What's missing is the
piece in the middle: the code that drives a **model** to turn an instance into a change-set, and the
runner that loops instances → propose → score → report.

The existing `research/harness/` already gives a provider-agnostic `LLMClient` (`base.py`,
`openai_compat.py`, `anthropic_client.py`, `mock.py`) selected by `config.py`, plus ik_llama serving
in `serving/`. The target models are 30B-class local (Gemma 4 / Qwen 3.6 at Q4 on a 24 GB 3090,
comfortable at 8–16K context) with a BYOK frontier option. Prior A/B work runs greedy + fixed seed.

## Goals / Non-Goals

**Goals:**
- One **propose core** that maps `Case → ChangeSet`, identical for golden and real cases.
- A **golden eval runner** that scores that core against held-out languages and emits comparable results.
- A clean, typed **contract** (Case / ChangeSet / Scorer) so this harness and the sibling golden work
  interoperate without import-level coupling.
- **Direct local control** for 30B reliability: deterministic context, constrained decoding, strict
  validation, reproducible (greedy/seed) runs.
- Runnable end-to-end **offline** (mock backend + fixture) while real golden data lands.

**Non-Goals:**
- C# port; real `.fwdata` ingestion; parallel-translation-QA gold; RL *training* (only the pure
  reward-fn seam); the linguistic *content* of primers/skills beyond a minimal working version;
  ownership of the ablator/scorer/instances (sibling agent).

## Decisions

- **The propose core is backend-, golden-, and answer-key-agnostic.** `propose(case, client, cfg) ->
  ChangeSet`. Golden eval is just `score(instance, propose(instance.case, ...))`. *Alternative:* two
  separate code paths for eval vs production — rejected; it would let them drift, defeating the whole
  bet.
- **Contract via structural `Protocol`s, not shared concrete classes.** Define `Case`, `ChangeSet`
  (lists of `lexical/*` + `morphophonology/*` ops), `ScoreResult`, and `Scorer` as Protocols/dataclasses
  in `research/proposal/contract.py`. The runner adapts the sibling's concrete instance/scorer to these
  shapes. *Alternative:* import `research.golden.*` directly — rejected; hard-couples two
  simultaneously-changing trees. A shared fixture both sides validate against keeps us honest.
- **Harness-orchestrated retrieval; no vector search, no model tool-calls.** Context = compiled primer
  + deterministically selected case facts. *Alternative:* agentic retrieval (model calls tools) — fine
  for frontier, unreliable at 30B (esp. Gemma); rejected for the default tier. Embedding RAG —
  rejected (nondeterministic).
- **Constrained decoding + strict validation, per backend.** GBNF `grammar` through the
  `openai_compat` kwargs seam for ik_llama; `json_schema` for Anthropic/BYOK; every op validated
  (jsonschema/pydantic) before it counts. *Alternative:* trust free-form JSON — rejected; a 30B emits
  invalid ops too often. Inventory-specialized GBNF (restrict POS/morph-types/headwords to the
  language's own symbols) is the strong form — start with the static change-set grammar + validation,
  add inventory specialization as a fast-follow.
- **Reuse the `LLMClient` kwargs seam for direct control; stay on the OpenAI-compat contract.** Pass
  `cache_prompt`/`grammar`/`seed`/`n_keep` via `**kwargs` (already supported by `openai_compat.py`).
  *Alternative:* a bespoke llama.cpp-native client — deferred; only KV slot save/restore needs the
  native endpoint, which is out of scope for this change.
- **Determinism by default:** temperature 0 / greedy, fixed seed, single-slot serving; results carry
  model+seed+config for reproducibility, matching existing results conventions.
- **Module layout:** `research/proposal/` = `contract.py`, `context.py` (primer + retrieval assembly),
  `grammar.py` (change-set GBNF/JSON schema), `change_set.py` (parse + validate ops), `propose.py`
  (the core). `research/eval/` = `instances.py` (load golden via contract), `runner.py`,
  `report.py`, plus a `fixtures/` tiny case + `stub_scorer`.

## Risks / Trade-offs

- **Contract drift with the sibling agent** → publish `contract.py` + a shared fixture instance early;
  both sides assert against it; coordinate the instance/scorer shape before deep implementation.
- **30B may not reach "pretty well"** → that *is* the experiment; mitigations are structural
  (constrain output, decompose to small decisions, the deterministic HC gate catches errors regardless
  of model strength, and `guess/ask/defer` routes the hard tail to BYOK/human). The runner's paired
  arms make the local-vs-BYOK gap measurable.
- **GBNF on ik_llama's chat endpoint may differ from native** → detect support; if absent, fall back to
  `json_schema`/best-effort and lean on strict post-validation (which is mandatory anyway).
- **Golden data not ready** → mock backend + fixture instance + stub scorer keep the loop green in CI;
  swap to real instances/scorer behind the same contract.
- **Spurious ambiguity (the golden design's "silent killer")** is scored by the sibling's scorer — the
  runner must surface it in diagnostics, not hide it behind a single reward number.

## Migration Plan

Purely additive (new `research/proposal/` + `research/eval/`); no existing behavior changes, so no
rollback needed. Land contract + mock loop first (CI green), then wire the real golden instances/scorer
as the sibling agent publishes them, then run the first real 30B-vs-BYOK sweep.

## Open Questions

- Exact on-disk **instance** shape and **Scorer** signature the sibling agent settles on (coordinate;
  the Protocol absorbs reasonable variation).
- Whether inventory-specialized GBNF lands in this change or the next (default: next; static grammar +
  validation now).
- Primer compilation depth for golden cases (which are corpus-bootstrapped, not full FLEx projects) —
  start minimal, expand as the primer spec firms up.
