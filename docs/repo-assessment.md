# Repo assessment & cleanup plan

_Snapshot: 2026-06-22. ~14k lines of Python across 17 `research/` modules; Stage 1 (Python research) only —
no `src/` C# yet. Eight OpenSpec changes (three now archived into canonical specs)._

This is a living worklist. Check items off as they land. Workstreams are roughly independent; **1 (hygiene)**
and **3 (gold principle)** are cheap and unblock the rest.

---

## Decisions of record

These are settled — encode them, don't relitigate.

1. **Staging: prototype-first, C# later.** Python keeps refining the TDD cycle. The next build is a
   **throwaway web UI to dream about "working through issues"** (the deferral-ticket review UX) — *not* the
   C# core. C# (`src/`, net10 packable libs) is written only when we're past prototyping and a thin language
   is proven. The empty `src/` is correct for now.
2. **OpenSpec is the system of record.** Completed changes are **archived** (apply → `openspec archive` →
   canonical `openspec/specs/`). Don't leave finished work as a dangling proposal.
3. **The frontier is tgl/swh morphology**, recovered via **morpheme-alignment + Gemma + deferral tickets** —
   the stack just built. spa/ind are proven; further spa polish is not the research edge. This is *why* C#
   is deferred and *what the system is being built to do*.

### The gold principle (sharpened)

> **The reference gold is ONLY an internet-backed, Opus-assisted, cross-verified standard for improving and
> assessing the parts of the TDD loop.** It is the *yardstick*, never a second grammar-builder.

Implications:
- `golden/reference/` (UniMorph/UD/Wiktionary/unfoldingWord + Opus cross-verification) measures the cycle;
  it must not drift into *inducing* the grammar itself. Induction lives in `cycle/` (+ `align/`).
- Thin reference coverage (tgl/swh ~0.04) is a **yardstick-coverage gap to close with internet data + Opus**,
  not a reason to abandon reference or to let the cycle grade itself.
- The cycle is never assessed against its own output — always against the independent reference standard.

---

## Workstream 1 — hygiene / tear-up (do first, cheap) — ✅ DONE 2026-06-22

- [x] Deleted the three README-only stub dirs; READMEs moved to `docs/plans/{data-gen,data-prep,models}-plan.md`.
- [x] Removed `llama.log` (root) + `research/llama.log`; `*.log` and `.cache/` were already gitignored.
- [x] Demoted `cycle/morph_align.py` — docstring now states it is the *no-HC offline-only* quick path,
      superseded for the verified path by `align/morph_align_hc.py`.
- [x] Swept: no tracked `*.log` / `__pycache__` / `.egg-info` remain; fixed a stale `data_gen/README.md`
      docstring pointer in `harness/anthropic_client.py`. Core suites green (47 offline tests pass).

## Workstream 2 — consolidation (stop the rot)

- [ ] **Collapse the four phonology modules into one.** Today: `cycle/phonology.py`, `cycle/hc_phonology.py`,
      `golden/reference/phonology_gold.py`, `golden/reference/phonology_induce.py`. Target: one induction +
      emission module (the HC archiphoneme/harmony path) with the reference side consuming it as a check.
- [ ] **Audit `parsegym/`.** Only `questions.py` is reused (by `deferrals/`). Decide the fate of
      `curate.py` / `assess.py` / `gym/` now that `deferrals/validation.py` generates ablation scenarios —
      keep `questions.py`, retire or fold the rest.
- [ ] **Clarify the three eval harnesses' boundaries** in their module docstrings: `eval/` = proposal-loop
      scoring, `deferrals/pipeline.py` = per-stage deferral scoring, `benchmarks/linggym` = LLM calibration.
      No merge needed — just make the non-overlap explicit so they stop looking redundant.
- [ ] **De-duplicate segmentation** shared by `cycle/` and `golden/reference/` into one segmentation lib
      (consumed by both induction and the morpheme stream).

## Workstream 3 — enforce the gold-as-yardstick principle

- [x] State the principle (above) at the top of `golden/reference/README.md` and in `AGENTS.md`. _Done 2026-06-22._
- [ ] Add a guard/check that the cycle is **only ever scored against the reference standard**, never its own
      output (a test or an assertion in the scoring path).
- [ ] Close the tgl/swh yardstick gap with **internet data + Opus cross-verification** (the reference
      compiler's job): add Wiktionary/whatever sources exist for tgl/swh, Opus-verify, raise reference
      coverage from ~0.04 so the yardstick can actually measure those languages.

## Workstream 4 — OpenSpec discipline

- [x] Archive the three 100%-complete changes → canonical specs (`audio-evidence-addon`,
      `audio-word-candidate-playback`, `phonology-induction-loop`). _Done 2026-06-22._
- [x] Resolve the near-done changes — **decided: keep both active**. `deferral-packages` (65/66) and
      `morpheme-alignment` (16/18) have genuine follow-on tasks (optional Apertium signal; gated HC
      round-trip + the full 4-lang run), not paperwork — archiving would falsely imply completion. Revisit
      once those tasks land. _Decided 2026-06-22._
- [ ] Triage the older partial changes: `assess-grammar` (13/21), `apertium-alignment-bridge` (14/17),
      `eval-proposal-loop` (21/23) — finish, descope, or archive each. No indefinite half-states.
- [ ] Adopt the rule going forward: a change is *done* when applied + archived; `openspec/specs/` reflects
      reality.

## Workstream 5 — the "working through issues" web UI — ✅ BUILT 2026-06-22 (`deferrals/webui.py`)

A **throwaway** local web app (stdlib `http.server`, **no new deps**) that renders the deferral tickets as
a bug-tracker queue a linguist works one-by-one. Run:
`uv run python -m deferrals.webui --pair spa --seed-demo --port 8765`.

- [x] Read path: prioritized queue (impact/confidence/deps); open a ticket → `render(ticket)` markdown →
      HTML (hypotheses + counterfactual parses + speaker questions). Verified serving live.
- [x] Resolve path: the three actions (accept option / accept + words / reject + reason) POST through
      `TicketStore.resolve` → `deltas/` (reuses the existing write path; the UI adds no logic).
- [x] Disposable: pure consumer of `deferrals/` functions; stdlib only; demo-seed so it runs without a
      live Gemma run. Lessons (not code) graduate to the C# loop console later.
- [ ] _Follow-on:_ after a resolve, show what `pipeline.recycle` re-scored/promoted (the loop closing) —
      deferred because `recycle` needs HC; currently the resolve confirmation shows the delta ops written.

## Workstream 6 — the frontier experiment — ✅ RUN 2026-06-22 (see `docs/w6-coverage-experiment.md`)

- [x] Ran/measured the frontier: NT inventory + TDD ceiling (spa .975 / ind .60 / swh .60 / tgl .39) +
      residual composition (names vs morphology) + the internet-affix lever (spa 1597 affixes → .93;
      tgl 0 affixes → ~0) + live Gemma lift on the swh needy tail (3/20 accept @ 100% precision, 17 defer).
- [x] **Verdict — the thesis holds, with a sharpened goal:** target **~95% TOKEN coverage via a generative
      grammar**, not 100% of the 17k-form type tail (40–63% hapax). TDD gets the core; the internet
      (affixes/classes for tgl/swh) and Opus (glosses/functions/irregulars, HC-verified, accept/defer) get
      the rest; NER handles the proper-noun tail; the irreducible residual is the deferral queue (by design).
- [ ] _Blocked on W3:_ score against the reference yardstick once tgl/swh affix/class coverage is raised
      (today the yardstick is too thin to grade the frontier — tgl reference has 0 affixes).
- [ ] _Gap-closing tasks moved to `docs/w6-coverage-experiment.md`_ (internet affixes for tgl/swh,
      generative swh noun-class morphology, Opus run, NER pass, token-coverage reporting, tgl cycle parity).

## Workstream 7 — target layout & dependency contract (future, after 1–3)

Group modules by **role**, with a one-way dependency flow
(`corpus → {induce, align} → propose → review → gold`; `engine` + `assess` are leaf utilities):

```
corpus/   ← datasets/ebible          engine/  ← golden/{grammar,hc,ablate}
gold/     ← golden/reference + golden_sets + goldio   (the yardstick + frozen gold)
induce/   ← cycle/ + ONE phonology    align/   ← align/
propose/  ← proposal/ + harness       review/  ← deferrals/ + deltas/
assess/   ← assess/                   eval/    ← eval/ + benchmarks/ + parsegym(questions)
addons/   ← audio/ + bilingual/       (optional, clearly fenced)
```

- [ ] Write the dependency contract (what may import what) into `AGENTS.md` **before** moving files, so the
      tangle stops growing even if the physical move waits.
- [ ] Physically regroup only once the contract is settled and Workstreams 1–3 are done (avoid churn).

---

## What is load-bearing (do not break)

`proposal/change_set.py` + `contract.py` (the canonical op vocabulary every module imports), `harness/`,
`golden/{grammar,hc}.py` (the HC oracle), `deltas/` (the write ledger), `datasets/ebible/` + `golden_sets/`
(corpus + frozen gold). Recent and well-tested: `deferrals/` (39 tests), `align/morph_align_hc.py`,
`assess/`. The `linguistics/` markdown (primitives + meta-workflows) is the conceptual backbone — keep and
keep current.
