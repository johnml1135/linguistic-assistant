# eval/

The **golden eval runner** — wraps the `proposal/` core with the golden **scorer** and produces
reproducible results. Eval-only; the propose core it calls is identical to production.

```
instances ──▶ propose() ──▶ Scorer.score(instance, change_set) ──▶ records ──▶ results JSONL
```

## Run it

```bash
# offline smoke test — no model, no network, no golden data
python research/eval/run.py --fixture

# local 30B over real golden languages (start serving/run-ik-llama-server.ps1 first)
python research/eval/run.py --endpoint ik_llama --glottocodes lezg1247,tsez1242 --tier hard

# BYOK frontier arm over the same instances (needs ANTHROPIC_API_KEY)
python research/eval/run.py --endpoint opus --glottocodes lezg1247,tsez1242 --tier hard
```

Results land in `research/benchmarks/results/` (`<name>.jsonl` + `<name>.summary.json`), mirroring the
existing `ab_*` conventions (model, seed, config, reward, diagnostics).

## Modules
- `instances.py` — **adapter** to the sibling golden-set layout (`research/golden/<glottocode>/`).
  Best-effort until the ablation/instance manifest is finalized — reconcile with the golden-set agent.
- `stub_scorer.py` — a clearly-labeled **stub** so the loop runs before the real HC scorer exists.
  **Not** the golden scorer; `run.py` auto-uses the real one (`golden.scorer.build_scorer`) when importable.
- `runner.py` — the loop; never computes correctness itself (delegates to the `Scorer`).
- `report.py` — per-instance + summary output.
- `run.py` — CLI (endpoint, languages, tier, seed, arms).
- `fixtures.py` — toy instance + `MockProposer` for the offline path.

## The contract with the golden-set agent
This runner depends on `proposal/contract.py` (`Instance`, `Scorer`, `Case`, `ChangeSet`) and the
on-disk golden layout — not on golden's concrete classes. The fixture in `fixtures.py` is the shared
shape both sides validate against. Open items: exact instance manifest + `Scorer` signature (tasks
5.1 / 5.2 / 6.4).
