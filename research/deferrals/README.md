# deferrals/ — resolution tickets for deferred linguistic decisions

When the lexical/affix proposer or sense-picker **defers** ("I don't know, ask a human"), this package
turns the one-line `defer` record into a reviewable **resolution ticket**: a strict JSON + markdown
package with auto-enumerated hypotheses (each a typed HC grammar edit), HC-verified counterfactual parses
("if A were true, this verse parses thus"), 5–10 scripted speaker questions, triage tags, and a structured
resolution that flows back to the gold through the `deltas/` ledger.

The deterministic spine runs with **no LLM**; the model only adds reach (out-of-taxonomy hypotheses) and
readable prose, and HC verifies everything it proposes.

## The 4-stage cyclical pipeline

| Stage | Module | What it does | Error tolerance |
|---|---|---|---|
| **1. Auto-accept** | `auto_accept.py` | sweep gloss/POS where THOT ∩ a high-conf LLM check concur | **≥ the per-language bar** (profile; default 99.5%); `ai-auto`, auditable, revertible; lexical only |
| **2. Candidate selection** | `select.py` | rank failing forms by impact × resolvability; cluster forms→one lexeme; worst-part suspects | recall-oriented |
| **3. Hypothesis generation** | `taxonomy.py` (+ `enrich.py` LLM) | typed HC edits per deferral type; profile-pruned | over-generation OK — stage 4 filters |
| **4. Assessment** | `assess.py` | net parse Δ (gains−regressions) + **ΔMDL** (`assess/mdl`) + acceptance gate | high-precision: a wrong accept corrupts the gold |

The loop is **cyclical** (`pipeline.recycle`): resolving a ticket re-scores its dependents; one that has
become resolvable is promoted, one invalidated is re-opened — iterating to convergence.

## What is AUTOMATIC vs needs an LLM

Everything enumerable from HC's resolution space or computable from the corpus is **automatic**: the
taxonomy, the counterfactual parses, impact/dependency/confidence tags, presentation-option selection, the
metric assessment, the ablation validation set. The LLM (`enrich.py`, `skills/package_builder.md`) only
supplies **reach** (hypotheses the taxonomy lacks) and **readability** (prose) — and every model
hypothesis is HC-verified before it enters a ticket. Phase A alone yields a complete, correct ticket.

## Modules

- `schema.py` — `DeferralTicket` / `Hypothesis` / `GrammarEdit` / `PresentationOption` / `Resolution` (+ JSONL I/O).
- `edits.py` — typed grammar-edit ops over `golden.grammar.LangModel`; `apply_edits` clones, never mutates the gold.
- `counterfactual.py` — deterministic related-verse selection + HC re-parse/diff (`now` vs `if-hypothesis`).
- `taxonomy.py` — deferral type → candidate hypotheses; profile-filtered (no Spanish infix, no Swahili gender).
- `build.py` — assembles a ticket; `python -m deferrals.build --pair <p>` backfills from `defer` records.
- `store.py` — the tracked `deferrals/<pair>/tickets.jsonl`, the lifecycle (open→in_review→resolved|wont_fix),
  and the resolution → `deltas/` write-back (human decisions are locked).
- `render.py` — markdown view, derived only from the ticket JSON.
- `assess.py` — Stage 4: net parse delta + ΔMDL + scorecard deltas; the regression gate.
- `validation.py` — the ablation validation set (remove a known item → ground-truthed scenario + decoys).
- `select.py` — Stage 2 selection (impact × resolvability, forms→lexeme clustering, worst-part suspects).
- `auto_accept.py` — Stage 1 tier (two-signal concurrence, per-language bar, `ai-auto`).
- `pipeline.py` — `score_pipeline` (per-stage metrics vs the ablation set) + `recycle` (cyclical re-eval).
- `enrich.py` — Phase B LLM enrichment (additive, HC-gated, graceful without an endpoint).
- `profile.py` + `feature_explanations.py` — the per-language profile (constrain + configure) with
  pre-written, open-licensed, non-linguist feature explanations.

## How resolutions reach the gold

A reviewer records exactly one action — `accept_option`, `accept_with_words`, or `reject_with_reason`. A
non-reject action maps the chosen hypothesis's typed edits onto `proposal.change_set` ops and writes them
into `deltas/store/<pair>.deltas.jsonl`, locked as a human decision. The gold is mutated **only** through
that ledger + its appliers — never from here.

## Tests

`uv run --with pytest python -m pytest deferrals/tests_smoke.py` — the offline tests need no `hc`/LLM;
the HC-gated tests (counterfactual flip, ablation true-vs-decoy, pipeline scoring) run when `hc` is
installed and are skipped otherwise.
