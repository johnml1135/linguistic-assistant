# proposal/

The **shared propose core**: `Case → ChangeSet`. The exact same code evaluates a model on golden
(answer-keyed) cases and proposes edits on real (unknown-answer) FLEx projects — golden cases are just
real cases with an answer key.

```
Case ──▶ assemble_context (primer + harness-orchestrated retrieval)
     ──▶ client.complete (GBNF grammar | json_schema constrained, greedy, seeded)
     ──▶ validate_change_set ──▶ ChangeSet | ValidationFailure
```

## Modules
- `contract.py` — the cross-agent seam: `Case`, `IGTRecord`, `ChangeSet`, `ScoreResult`, and the
  `Instance` / `Scorer` **Protocols** (no import of `research/golden`). Stdlib-only; both sides depend on it.
- `change_set.py` — op vocabulary (`lexical/*`, `morphophonology/*`), parse + **strict validation**
  (invalid output is rejected, never coerced), and `op_signature` for scoring/diffing.
- `grammar.py` — `change_set_gbnf()` (llama.cpp/ik_llama `grammar` kwarg), `change_set_json_schema()`
  (Anthropic/BYOK), and a compact `schema_hint()` for the prompt.
- `context.py` — `compile_primer()` (byte-stable language card) + deterministic retrieval +
  `assemble_context()`. No model tool-calls, no vector search.
- `propose.py` — `propose(case, client, cfg)`; direct local control via the `openai_compat` kwargs seam
  (`grammar`, `cache_prompt`, `seed`).

## Backends
Selected by config via `harness/registry.build_client` — `ik_llama` (local 30B, default) or `opus`/BYOK.
`ProposeConfig.backend_kind` decides grammar (local) vs `json_schema` (Anthropic). Greedy + fixed seed
⇒ reproducible proposals.

## Status / follow-ups
- GBNF is currently coarse (valid-JSON); strict validation does the fine-grained checking. The strong
  form — GBNF generated from the language's own POS/morph-type/headword inventories — is a fast-follow.
- See `openspec/changes/eval-proposal-loop/` for the full spec/design/tasks.
