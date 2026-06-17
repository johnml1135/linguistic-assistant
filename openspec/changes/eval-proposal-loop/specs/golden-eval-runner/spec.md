## ADDED Requirements

### Requirement: Iterate golden instances via the contract
The runner SHALL discover and load golden instances from `research/golden/` using the agreed
instance contract, without re-implementing instance generation (owned by the sibling golden-set work).
It SHALL select instances by language (glottocode), difficulty tier, and/or ablation seed.

#### Scenario: Run a named language set
- **WHEN** the runner is pointed at one or more glottocodes present under `research/golden/`
- **THEN** it yields every instance for those languages at the requested tier(s) for evaluation

### Requirement: Score via the golden scorer protocol
The runner SHALL pass each proposal to the golden **Scorer** — a `(instance, proposal) → ScoreResult`
function — and SHALL treat its reward (∈ [0,1], gated on Hermit Crab non-regression per the golden-set
design) as authoritative. The runner SHALL NOT compute correctness itself; it depends on the Scorer
protocol and adapts to the sibling agent's concrete scorer when available, falling back to a stub
scorer only for pipeline tests.

#### Scenario: Reward comes from the deterministic scorer
- **WHEN** a proposal is produced for an instance
- **THEN** the runner invokes the Scorer and records the returned reward and diagnostics verbatim

#### Scenario: Stub scorer keeps the loop runnable pre-integration
- **WHEN** the concrete golden scorer is not yet importable
- **THEN** the runner uses a clearly-labeled stub scorer so the end-to-end loop still executes and is testable

### Requirement: Reproducible results output
The runner SHALL emit per-instance and summary results as JSONL mirroring
`research/benchmarks/results/`, capturing model/endpoint, seed, config, reward, and diagnostics, so
runs are comparable and reproducible.

#### Scenario: Results are written in the established format
- **WHEN** a run over an instance set completes
- **THEN** a per-instance `*.jsonl` and a `*.summary.json` are written with the run's model, seed, and
  per-instance rewards, comparable to existing `ab_*` results

### Requirement: Paired backend and skill sweeps
The runner SHALL support running the same instance set across multiple backends and skill/prompt
variants on identical items (paired), so a 30B model, a BYOK model, and skill variants can be compared
the way the existing A/B summaries are.

#### Scenario: Same items across arms
- **WHEN** two arms (e.g. local-30B vs BYOK, or skill-on vs skill-off) are run
- **THEN** both evaluate the identical instance set and the summary reports per-arm reward and the paired delta

### Requirement: Eval/RL firewall and no-network CI run
The runner SHALL keep the frozen evaluation split separate from any sampled-for-RL data, and SHALL be
runnable end-to-end with no model and no network via the mock backend and a fixture instance.

#### Scenario: Mock run produces a valid report offline
- **WHEN** the runner is invoked with the `mock` backend on the fixture instance
- **THEN** it completes with no network access and writes a valid results file
