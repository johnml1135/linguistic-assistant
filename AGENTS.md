# AGENTS.md

Guidance for AI agents (and humans) working **on** this repository. For what the project *is*,
read [README.md](./README.md) first.

## What this repo is

A research/exploration tool: an AI **quality-assurance and language-documentation assistant** for
low-resource languages in the FieldWorks ecosystem. It helps teams enrich the lexicon, gloss and
validate wordforms (morphology via Hermit Crab), and **review translated text against parallel
sources**. It produces **change-sets (text files)** that a separate effort ingests into FieldWorks.
It does **not** generate translations — that is a separate fine-tuned NLLB-200 model (SIL's Serval).

## Non-negotiable scope rules

1. **QA + documentation, not translation.** This tool *checks* translations and *documents* the
   language; it never *generates* target text. Machine translation is a separate fine-tuned NLLB-200
   model (Serval). **Do not** add, propose, or scaffold MT / Apertium / transfer-rule generation —
   FLExTrans / Apertium were evaluated and explicitly ruled out (translation is the NLLB model's job).
2. **Auto-propose rules only where engine + oracle both exist.** Morphology qualifies (Hermit Crab +
   golden `word → gloss` set). Do **not** induce a syntactic grammar we cannot verify; cross-word and
   agreement checks ride on the **gold structure of the parallel source**, not on a parser we build.
   Don't use "grammar" loosely: the morphosyntax the parser needs (POS, inflection class, features,
   affix templates) is **in**; sentence-syntax *induction* is **out**.
3. **Parallel alignment is core from v1 — not an add-on.** Aligned parallel text is a first-class
   input, and evaluation uses **two gold sets**: monolingual `word → gloss` (deterministic, Hermit
   Crab) and parallel QA (LLM-judgment, precision/recall). Many headline outputs are parallel-driven
   (missing sense, number/agreement mismatch).
4. **Hermit Crab is the only parser engine.** Both the output format and the parse-failure oracle.
   **Do not** add, propose, or scaffold XAmple support or a multi-engine ensemble — it was explicitly
   killed, not deferred.
5. **This repo writes text files, not databases.** Never write to `.fwdata`, drive the FLEx GUI,
   or take a runtime dependency on a FieldWorks install or `flexlibs`/`FlexToolsMCP` for the core
   loop. The output is change-sets; ingestion into FLEx is a *separate* project.
6. **Cross-platform, git-native.** The authoring/truth plane must run anywhere (the dev box here
   is Windows + PowerShell, but the loop itself should not require Windows). Hermit Crab is reached
   via the `dotnet tool` (`SIL.Machine.Tool`) or the `SIL.Machine` NuGet — both managed/portable.

## Architecture in one breath

Two planes. **Authoring/truth plane** = this repo: Hermit Crab ruleset (XML), lexicon, golden test
set, issue backlog, change-sets, skills — all plain files in git. **FLEx sync plane** = a separate
Windows effort that ingests our change-sets. Keep them decoupled.

Three axes, don't conflate: **data/two-plane** (above), **maturity/three-stage** and
**runtime/offline-online** (below). Full design:
`docs/superpowers/specs/2026-06-16-runtime-and-staging-architecture-design.md`.

## Maturity stages — this repo holds stages 1 and 2

1. **`research/` — Python playground.** Idea iteration (prompts/skills, RAG, evaluation). Promotes
   out when it reliably emits valid change-sets that pass the golden gate.
2. **`src/` — C#/.NET 10 validation program.** Builds/validates HC rules, makes LLM calls, parses,
   produces/applies change-sets, plus a **sample UI**. This is the stage agents mostly work in.
3. **Product split-off (downstream).** The proven C# **core** → NuGet package or migration into
   FieldWorks / FieldWorks Lite / Paratext 10.

Rules for agents:

- **Target `net10.0`** for all C# (the TFM FwLite uses, so the core can later be referenced in-process).
- **The sample UI is throwaway; the engine is the asset.** Keep the core in UI-free, individually
  packable libraries (`HermitCrab`, `ChangeSets`, `Proposer`); the web host (`Console`) is a
  disposable consumer that owns no logic. Do not let logic leak into the host.
- **Cross-stage contracts are the change-set schema and portable skills** (markdown + tool contracts).
  A skill promoted from `research/` moves as *data*, not a rewrite — keep skills provider-portable.
- Stage boundaries are **promotion gates**, not folders: stage 1→2 = passes the golden gate; stage
  2→3 = the loop closes measurably on a real language.

## Runtime — the LLM is not co-located with the user

The loop is split so only the *proposal* step needs connectivity:

- **Offline half (local, no GPU):** HC parse → backlog, human review, apply deltas, the golden-set
  gate, git. Hermit Crab is managed .NET — the oracle and safety gate never need the cloud.
- **Online half:** proposals via a **swappable endpoint** (`Microsoft.Extensions.AI` `IChatClient`).
  Shipped default = SIL-hosted open model; **BYOK-frontier** = opt-in connected mode.

Rules for agents:

- **Inject the `IChatClient`; never hardcode a provider.** Frontier/SIL-hosted/local must be a config swap.
- **Keep everything except the proposal call offline-capable.** If a feature needs the network outside
  step "propose," stop and flag it — it belongs in the (deferred) job-queue sync subsystem, not the core loop.
- **Data egress is explicit, visible config**, never a side effect of which endpoint is set.

## The change-set contract

Change-sets are the product. Treat their schema as a contract with the downstream ingestion effort.

- Two operation vocabularies:
  - `lexical/*` — mirror **MiniLcm** vocabulary (entries, senses, examples, POS, semantic domains)
    so they can later be lowered onto the LexBox/Harmony path. Do **not** adopt CRDT machinery —
    our edits are sequential (AI proposes, human reviews), not concurrent merges.
  - `morphophonology/*` — our own schema, expressed against Hermit Crab grammar constructs
    (phonological rules, natural classes, allomorph environments, affix templates, strata).
- Every operation carries: **rationale, confidence, impact, provenance** (link to the corpus
  evidence that triggered it).
- Change-sets are reviewable as plain text. Prefer formats that diff cleanly.
- Use **explicit move operations** for reordering rules/strata/slots — never model a reorder as
  delete-then-reinsert (under concurrency that duplicates the element). Order-bearing lists are
  edited as atomic, reviewable operations.

## Sync & merge: git, not CRDT — and never blind merge

The Hermit Crab grammar is **not** a CRDT and must not be made one. We evaluated extending SIL's
Harmony CRDT to carry HC rules and **rejected it**: a CRDT guarantees convergence, not validity,
and HC's grammar is all validity (rule order = meaning, references must hold, strata must be
consistent — non-monotone invariants that conflict-free merge provably cannot preserve). Worse,
HC's loader **silently skips** a stratum's missing rule id, so a blind merge can yield a
valid-looking grammar that parses wrong with no error.

Rules for agents:

- **A morphology conflict is resolved by a human, or by AI with human approval — never by
  auto-merge.** The grammar is a versioned text artifact reconciled with git-style 3-way merge that
  **surfaces** conflicts for review. Do not write code that silently auto-resolves grammar
  conflicts.
- **CRDT sync is for the `lexical/*` tier only.** Do not put `morphophonology/*` data under any
  CRDT/auto-merge path.
- Keep `morphophonology/*` operations expressed as explicit, reviewable primitives (including move
  ops) — they are deliberately the same shape a future hybrid (CRDT object-bag + reviewed ordered
  lists) would need, so don't design them into a corner.

## The golden-set safeguard (do not skip)

Hermit Crab applies *ordered* rewrite rules, so a mis-ordered-but-plausible rule produces a
*silently wrong* parse, not a visible failure. Therefore:

- Maintain an **editable golden set** of known `word → gloss` pairs (Hermit Crab's `TestCommand`
  supports this).
- Any proposed rule change must be evaluated for **regressions against the golden set**, not just
  "did the unparsed-word count drop." Report both. Test **parse and generate** — order affects both
  directions (HC analyzes with rules reversed).
- Every edit/merge/round-trip runs a **validate-and-repair pass**: explicit dangling-reference
  detection (including the rule ids HC silently skips) and segment/strata-consistency checks.
  "It loaded fine" is **not** evidence of a correct grammar — HC will load a broken one without
  erroring.

## The reference gold is a yardstick, not a grammar-builder

There are two distinct "gold" notions; do not conflate them.

- **`golden_sets/` (frozen) + `golden/{grammar,hc}`** — the monolingual `word → gloss` regression gate
  (the deterministic safeguard above).
- **`golden/reference/`** — an **internet-backed, Opus-assisted, cross-verified standard whose ONLY job is
  to improve and assess the parts of the TDD loop** (`cycle/` + `align/`). It is a *yardstick*.

Rules for agents:

- **The reference gold MUST NOT induce the grammar.** Induction lives in `cycle/` (+ `align/`); reference
  only *measures* it. Do not add grammar-building logic to `golden/reference/`.
- **The cycle is never scored against its own output** — always against the independent reference standard.
- **Thin reference coverage (tgl/swh) is a yardstick gap**, closed by adding internet sources + Opus
  cross-verification — not by lowering the bar or letting the cycle self-grade.

## The skills layer is the point

The reason this beats a plain rule engine is AI judgment, packaged as **skills**: proposing rules
from evidence, and deciding between *guess now* / *ask a native speaker* / *defer for lack of
data*; prioritizing the backlog by confidence and impact; phrasing decisions a non-linguist can
answer. When in doubt, invest in the skills, not in more parser plumbing.

The local-vs-global **skill promotion** mechanism (project-specific skills adapting, then being
assessed for pull-back into the shared set) is **deferred** — get the base loop working on one
language first.

The *guess / ask / defer* decision is a concrete artifact, not just a prompt: a **deferral never
guesses — it emits a resolution ticket** (`research/deferrals/`). Rules for agents:

- **The deterministic spine must stay LLM-free and usable offline.** A model only adds *reach*
  (hypotheses the fixed HC-mechanism taxonomy misses) and *readable prose* — and **every** model
  hypothesis is HC-verified (real counterfactual re-parse) before it enters a ticket. Never let an
  unverified model claim into a ticket as confirmed.
- **A hypothesis IS a typed grammar edit**, ranked by the `research/assess/` metrics (ΔMDL, coverage,
  over-generation, Tolerance) and gated by a **regression check** — a fix that breaks other parses is
  rejected. Don't judge a hypothesis by "does the focus parse now."
- **The per-language profile constrains the solution space.** Respect it: never propose a mechanism the
  profile locks off (Spanish infix, Swahili gender). Profiles are falsifiable (probe → ΔMDL), seeded
  from WALS/Grambank, and carry open-licensed non-linguist explanations.
- **Resolutions reach the gold only through `deltas/`.** Never mutate the frozen golden set directly.

## Conventions

- **Shell:** primary dev environment is Windows PowerShell 7+; a Bash tool is also available. Use
  forward-slash paths in committed scripts where possible.
- **Git:** branch before non-trivial work; commit/push only when asked.
- **Decisions of record** live in the agent memory under
  `~/.claude/projects/.../memory/` (see `MEMORY.md`). When a scope or architecture decision
  changes, update memory as well as this file.
