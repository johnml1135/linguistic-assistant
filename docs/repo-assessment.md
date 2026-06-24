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
4. **The human owns the foundational cuts; the machine suggests + populates + flags.** The process is three
   committed phases — **switches → classes → exceptions** (`docs/workflow.md`). Noun/verb classes are a
   **human-declared schema** (the compile root: HC features, concord, rule scope all generate from it); the
   machine never auto-commits class boundaries. Rules are **ordered blocks** (default + exception classes +
   individuals) induced by recursive Tolerance; agreement is conditioning with a cross-word controller.
   Design in `docs/phonology-architecture.md` §8.

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

- [x] **Frontier finder built** (`review/frontier.py` + `docs/chunk-types.md`, 2026-06-24): the system
      AUTO-FINDS a language's next chunk of work from the data — a typed catalog of ~12 chunk types
      (orthography·switches·POS·affixes·morphotactics·classes·agreement·allomorphy·morphophonology·
      non-concatenative·exceptions·homographs), each with an unexplained-mass probe + readiness gate;
      ranks the ready chunks and names the next with evidence + action. Live (no hand-tuning): swh→agreement
      (computed the same thing I'd hand-picked from the 688), ind→affixes, tgl→POS, spa→classes. NEXT chunk
      is always the top TRUE coverage gap; count-based proxies (allomorphy) are flagged + excluded from the
      recommendation. 5 tests; 211 green. **This is the product** — working on unknown languages, per
      decision #4 / `docs/workflow.md`.
- [x] **Class-system lifecycle built** (`review/classes.py` + `class_schema` on `LanguageProfile`, 2026-06-24):
      suggest → declare → utilize, with the confidence tier (`route`: foundational class-system never
      auto-commits; leaf assignments auto-push when verified-confident, stamped + reversible). The declared
      schema is the **compile root** in the profile. Spanish live: suggest 2 genders (m 1141/f 929 + concord)
      → declare v1 → utilize 2070 nouns, 55 textbook exceptions (*día*, *mano*, *alma*=el-agua, *profeta*).
      Strategy-dispatched (Bantu noun-class co-cluster slots behind the same interface). 9 tests; 205 green.
      Implements `docs/workflow.md` §2 + the auto-push tier. Caveat: members ≈ "word after article" (some
      non-noun noise, e.g. *alimenta*) — same-morpheme/POS filter is the follow-on.
- [x] **Glide-collapse emitter + HC round-trip gate built** (`engine/hc_collapse.py`, 2026-06-24): turns a
      glide candidate into a real HC rule (`[+high,+syl]→[−syl]/__V`; one rule covers u→w & i→y) and
      VALIDATES it by round-trip, verified vs hc.exe. The gate (a) samples the rule's OWN counterexamples
      (`allomorph.member_words` — all distinct words, not top-k) and (b) judges in-environment items by the
      **Tolerance Principle** (`assess.metrics.tolerance_productive`). The gate is conservative and won't
      rubber-stamp: on swh all four glide families fail the Tolerance bar → DEFER. **Caveat (don't overclaim
      "unproductive"):** `member_words` has no morpheme filter, so the exception count is an UPPER BOUND
      contaminated by non-class-1 `mu*`/`mi*` forms (*muone*=verb+object-mu) — a tolerance *failure* is thus
      inconclusive (a *pass* would be sound). vi/vy + mi/my failures are genuine class members (robust
      defers); mu/mw is contaminated. 15 new tests; 196 total green. Follow-ons: filter members through the
      same-morpheme/gold-feature signal before counting; environment refinement / promote-with-exceptions
      (MDL); a syllabicity feature in `engine/hc.build_grammar_xml` for live application.
- [x] **Allomorph detector built** (`review/{allomorph,wordvec}.py`, 2026-06-23): generic detector for
      morphemes that mean the same but live in different environments (the dual of the constraint loop) —
      C phon-neighbor → A same-meaning + complementary-distribution → B conditioning, emitting
      `allomorph-collapse` change-sets for `promote.py`. Two key findings: (1) read **raw word-edges**, not
      the segmented stream (which fuses `mw/kw` to zero count); (2) meaning = **gold features** for
      grammatical morphemes (`mu≡mw`; rejects `hu/mu`), **word vectors** only for content (vectors rate all
      grammatical morphemes similar). Live (swh): finds the glide FAMILY `mu/mw`+`vi/vy`+`mi/my`. 13 tests.
- [x] **Constraint-induction loop built** (`review/{dossier,judge,constraints}.py` + `skills/generate_constraint.md`,
      2026-06-23): turns a homographic morpheme into environment-conditioned senses. THOT = dumb counter
      (co-occurrence), LLM = environment generator (`generate_constraint`), judge = **re-parse + distribution
      information-gain** (`I(source;bucket)` from a real split-token re-align) + most-constrained tie-break.
      14 offline tests incl. a plumbing test proving IG goes positive on a real split (so a "defer" is
      honest, not a silent bug). Live: swh `wa` ACCEPTS (IG 0.95 — word-initial=associative "of",
      non-initial=person marker "they/you"); `ku` splits (initial="to" infinitive, medial=object marker).
      **Scope: homograph judge only** — allomorphy (one English correspondence) scores ≈0 here and stays on
      the MDL/round-trip gate.

- [~] **Collapse the phonology modules into one pipeline — DESIGNED** (`docs/phonology-architecture.md`,
      2026-06-23): one morphophonology pipeline (substrate→detect→infer-UR→ordered-rule→verify→promote) with
      two evidence streams (text now, audio deferred), grounded in SPE/HC theory. Merge map + tasks in the
      doc; implementation pending. Biggest gap it surfaces: **rules need ordering + strata** (HC is SPE
      ordered-rule phonology; ours are a flat set).
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

## Workstream 7 — target layout & dependency contract — ✅ DONE 2026-06-22

- [x] **Physical role-based regroup executed** (on branch `refactor/role-based-layout`): `datasets→corpus`,
      `golden/{grammar,hc,ablate}→engine`, `golden/reference→gold`, `golden/_sources→_sources`,
      `cycle→induce`, `proposal→propose`, `harness→propose/harness`, `deferrals+deltas→review/`,
      `audio+bilingual→addons/`, `benchmarks+parsegym→eval/`. Imports + path constants + `parents[N]` depths
      rewritten (71 files); `.gitignore`/`pyproject` updated. **100 offline tests pass (= baseline).**
- [x] **Dependency contract written into `AGENTS.md`** — the one-way flow + leaf/consumer rules, incl.
      "`gold/` must not import induce/align/review/propose" (the yardstick rule as an import rule).
- [ ] _Remaining (W2, reframed by the regroup):_ the 4 phonology modules now split by role —
      `induce/{phonology,hc_phonology}.py` (building) vs `gold/{phonology_gold,phonology_induce}.py`
      (yardstick). Consolidate *within* each role (not across the induce/gold boundary) — the role split
      clarified the target. Also: dedup segmentation, audit `eval/parsegym` (only `questions.py` is used).

The achieved layout (one-way flow `corpus → {induce, align} → propose → review`, measured against `gold`;
`engine` + `assess` are leaf utilities; `addons`/`eval` are top consumers). Full contract in `AGENTS.md`.

---

## What is load-bearing (do not break)

`proposal/change_set.py` + `contract.py` (the canonical op vocabulary every module imports), `harness/`,
`golden/{grammar,hc}.py` (the HC oracle), `deltas/` (the write ledger), `datasets/ebible/` + `golden_sets/`
(corpus + frozen gold). Recent and well-tested: `deferrals/` (39 tests), `align/morph_align_hc.py`,
`assess/`. The `linguistics/` markdown (primitives + meta-workflows) is the conceptual backbone — keep and
keep current.
