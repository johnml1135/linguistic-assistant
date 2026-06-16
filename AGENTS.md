# AGENTS.md

Guidance for AI agents (and humans) working **on** this repository. For what the project *is*,
read [README.md](./README.md) first.

## What this repo is

A research/exploration tool: an AI assistant that helps field linguists do **word-level
morphological and phonological analysis** of low-resource languages in the FieldWorks ecosystem.
It produces **change-sets (text files)** that a separate effort ingests into FieldWorks.

## Non-negotiable scope rules

1. **Word parsing only — never syntax.** This is morphology and phonology. There is no syntactic
   grammar engine. Do not use the word "grammar" to describe the output; it is "word parsing" /
   "morphophonological rules." If a task drifts toward sentence-level syntax, stop and flag it.
2. **Hermit Crab is the only engine.** Both the output format and the parse-failure oracle. **Do
   not** add, propose, or scaffold XAmple support or a multi-engine ensemble — it was explicitly
   killed, not deferred.
3. **This repo writes text files, not databases.** Never write to `.fwdata`, drive the FLEx GUI,
   or take a runtime dependency on a FieldWorks install or `flexlibs`/`FlexToolsMCP` for the core
   loop. The output is change-sets; ingestion into FLEx is a *separate* project.
4. **Cross-platform, git-native.** The authoring/truth plane must run anywhere (the dev box here
   is Windows + PowerShell, but the loop itself should not require Windows). Hermit Crab is reached
   via the `dotnet tool` (`SIL.Machine.Tool`) or the `SIL.Machine` NuGet — both managed/portable.

## Architecture in one breath

Two planes. **Authoring/truth plane** = this repo: Hermit Crab ruleset (XML), lexicon, golden test
set, issue backlog, change-sets, skills — all plain files in git. **FLEx sync plane** = a separate
Windows effort that ingests our change-sets. Keep them decoupled.

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

## The skills layer is the point

The reason this beats a plain rule engine is AI judgment, packaged as **skills**: proposing rules
from evidence, and deciding between *guess now* / *ask a native speaker* / *defer for lack of
data*; prioritizing the backlog by confidence and impact; phrasing decisions a non-linguist can
answer. When in doubt, invest in the skills, not in more parser plumbing.

The local-vs-global **skill promotion** mechanism (project-specific skills adapting, then being
assessed for pull-back into the shared set) is **deferred** — get the base loop working on one
language first.

## Conventions

- **Shell:** primary dev environment is Windows PowerShell 7+; a Bash tool is also available. Use
  forward-slash paths in committed scripts where possible.
- **Git:** branch before non-trivial work; commit/push only when asked.
- **Decisions of record** live in the agent memory under
  `~/.claude/projects/.../memory/` (see `MEMORY.md`). When a scope or architecture decision
  changes, update memory as well as this file.
