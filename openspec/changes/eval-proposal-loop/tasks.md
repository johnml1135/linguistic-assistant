## 1. Contract & scaffolding

- [x] 1.1 Create `research/proposal/` and `research/eval/` packages (`__init__.py`).
- [x] 1.2 Define `research/proposal/contract.py`: `Case`, change-set op types, `ChangeSet`,
  `ScoreResult`, and `Scorer`/`Instance` Protocols (structural, no import of `research.golden`).
- [x] 1.3 Add a tiny shared fixture instance (`research/eval/fixtures.py`: raw IGT + ablated
  lexicon/grammar + answer key) both this harness and the sibling work can validate against.

## 2. Change-set schema & validation

- [x] 2.1 Define the change-set op vocabulary for `lexical/*` + `morphophonology/*`
  (`OP_TYPES` + JSON schema; rationale/confidence/impact/provenance fields).
- [x] 2.2 `research/proposal/change_set.py`: parse model output → `ChangeSet`; strict-validate every op;
  reject (don't coerce) invalid output, returning a typed `ValidationFailure`.
- [x] 2.3 `research/proposal/grammar.py`: emit a GBNF grammar and a JSON schema for the change-set
  (valid ops parse; malformed ops rejected — covered by `tests_smoke.py`).

## 3. Deterministic context assembly

- [x] 3.1 `research/proposal/context.py`: compile a minimal language **primer** from a Case
  (writing systems/POS/morph-type inventories, top-N entries, counts) with canonical, byte-stable
  serialization (sorted, no timestamps).
- [x] 3.2 Harness-orchestrated retrieval: deterministic selection of case-relevant lexicon/grammar
  facts + IGT, injected after the primer (no model tool-calls, no vector search).
- [x] 3.3 Test: identical inputs → byte-identical assembled context.

## 4. Propose core (backend-agnostic)

- [x] 4.1 `research/proposal/propose.py`: `propose(case, client, cfg) -> ChangeSet | ValidationFailure`.
- [x] 4.2 Direct-control kwargs for the local path (`grammar`, `cache_prompt`, `seed`) via
  `openai_compat`; `json_schema` for the Anthropic/BYOK path; `--no-grammar` fallback.
- [x] 4.3 Default backend = `ik_llama`, switchable to `opus`/BYOK by config with no code change.
- [x] 4.4 Test with the mock backend: `propose()` returns a schema-valid `ChangeSet` on the fixture.
- [x] 4.5 Test determinism: greedy + fixed seed → identical `ChangeSet` across two runs.

## 5. Golden eval runner

- [x] 5.1 `research/eval/instances.py`: load golden instances from `research/golden/` via the contract
  (best-effort adapter; final instance manifest to be reconciled with the sibling — see 6.4).
- [x] 5.2 Labeled **stub scorer** implementing the `Scorer` Protocol + auto-adapter to the sibling
  scorer (`golden.scorer.build_scorer`) when importable.
- [x] 5.3 `research/eval/runner.py`: loop instances → `propose` → `Scorer` → records (incl. diagnostics);
  correctness never computed in the runner.
- [x] 5.4 `research/eval/report.py`: per-instance `*.jsonl` + `*.summary.json` to
  `research/benchmarks/results/` (model/endpoint, seed, config, reward, diagnostics).
- [ ] 5.5 Paired-arm summary helper (local-30B vs BYOK; skill-on vs skill-off) over the identical
  instance set, with a paired-delta report like `ab_summary.md`. *(Follow-up; single-arm runs work now.)*

## 6. End-to-end & docs

- [x] 6.1 CLI entrypoint `research/eval/run.py` (backend, languages, tiers, seed).
- [x] 6.2 Offline CI path: `--fixture` (mock + fixture + stub) completes with no network and writes a
  valid results file (`tests_smoke.py` passing).
- [x] 6.3 `research/proposal/README.md` + `research/eval/README.md`: the contract, the shared core, and
  how to plug in the sibling's real instances/scorer.
- [ ] 6.4 Coordinate the contract (`contract.py` + `fixtures.py`) with the sibling golden-set agent;
  record any agreed instance/scorer shape adjustments. *(Cross-agent; in progress.)*
