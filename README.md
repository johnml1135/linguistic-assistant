# Linguistic Assistant

An AI assistant for field linguists working with **FieldWorks** / **LibLCM** data.

> **Status: research / exploration.** This repo is an early-stage investigation, not a
> production tool. Scope, formats, and architecture are still being shaped.

## What it is

Field linguists use SIL [FieldWorks Language Explorer (FLEx)](https://software.sil.org/fieldworks/)
to build dictionaries and morphological analyses of (usually low-resource) languages. FLEx
already runs a parser-in-the-loop: a morphological parser proposes analyses of words, and a
trained linguist approves or rejects them, word by word.

This project aims to **supercharge that loop** — not replace it. The goal is an AI layer that:

- **Proposes** lexical entries and morphophonological rules from corpus evidence, rather than
  just running a fixed parser.
- Works through a **batch backlog of issues** (unparsed words, conflicting analyses) with
  prioritization by confidence and impact, instead of grinding word-by-word in a UI.
- Makes contribution **accessible** — surfacing decisions a *non-linguist native speaker* can
  answer ("which of these three readings is right?"), not only ones requiring a trained linguist.
- Knows when to **guess, ask, or defer**: "I know enough to make a good guess" vs. "present
  options to a speaker" vs. "not enough data, move on."

The differentiator over pure rule-based parsing is this **judgment layer** (implemented as Claude
skills), not the parser itself.

## Scope

**In scope (v1):** word-level morphology and phonology — glossing, lexeme/allomorph discovery,
and morphophonological rule proposal.

**Out of scope:** sentence syntax / full "grammar" induction. The target engine (Hermit Crab) is
a *word-level* morphophonological parser; there is no syntactic engine here. We deliberately do
**not** use the word "grammar" for this reason — it is word parsing.

## How it works

### The engine: Hermit Crab

[Hermit Crab](https://github.com/sillsdev/machine) (the maintained implementation in
`SIL.Machine.Morphology.HermitCrab`, MIT-licensed, managed C#) is used as **both**:

1. **The output format** — the assistant emits a Hermit Crab ruleset (a single DTD-validated XML
   grammar: strata, phonological rules, natural classes, lexical entries, affix processes).
2. **The oracle** — running the corpus through the ruleset produces a machine-readable list of
   words it *fails* to parse, which feeds the issue backlog.

Hermit Crab both **parses** and **generates**, so a proposed rule can be verified round-trip
(generate the expected surface form, compare to what's attested). XAmple (FLEx's default parser)
is **not** used and is not planned — Hermit Crab only.

> **Safeguard:** Hermit Crab applies *ordered* phonological rewrite rules, so a plausible but
> mis-ordered rule can produce a *silently wrong* parse (not just a failure). Every proposed rule
> change is therefore gated by an editable **golden set** of known `word → gloss` pairs, checking
> for regressions — not merely whether the failure count dropped.

### Output: change-sets, not database writes

This repo **creates change-sets (deltas) as plain text files**. It does not write to FLEx
databases or drive the FLEx GUI. A **separate effort** ingests these change-sets into FieldWorks.

Change-sets are two-tiered, because the SIL ecosystem treats these data differently:

| Tier | Covers | Notes |
|---|---|---|
| `lexical/*` | entries, senses, examples, parts of speech, semantic domains | Shaped to mirror **MiniLcm** (the model behind [LexBox](https://github.com/sillsdev/languageforge-lexbox) / Harmony CRDT sync), so the ingestion effort *can* lower them onto that path later. |
| `morphophonology/*` | phonological rules, natural classes, allomorph environments, affix templates, inflection classes/features, strata | **Our own schema**, expressed against Hermit Crab grammar constructs. No structured delta format for this exists upstream — LexBox/Harmony deltas are lexicon-only. |

Every operation carries **rationale, confidence, impact, and provenance** (a link back to the
corpus evidence that triggered it), so the whole change-set is reviewable as plain text in git.

### Sync & merge model — git for the grammar, not a CRDT

We evaluated modeling the Hermit Crab grammar as a CRDT (extending SIL's
[Harmony](https://github.com/sillsdev/harmony) library, which powers LexBox sync). **We decided
against it.** A CRDT guarantees that replicas *converge to the same state*, but **not** that the
state is *valid* — and a Hermit Crab grammar is almost entirely about validity:

- **Rule order is meaning.** Phonological rules apply in order (feeding/bleeding/opacity); HC even
  applies them *in reverse* during analysis. A merge that converges to *some* order, as a CRDT
  does, can silently produce the *wrong* order — and so wrong parses.
- **The references must hold.** A valid grammar has no dangling references and consistent strata.
  These are non-monotone, deletion-sensitive invariants that — by the I-confluence / CALM results
  — pure conflict-free merge provably cannot preserve.
- **HC fails *silently*.** Its loader hard-errors on some dangling references but **silently skips**
  a stratum's missing *rule* id. So an automatic merge can yield a valid-*looking* grammar that
  parses incorrectly, with no error raised.

**Therefore: a morphology conflict gets a human- or AI-guided, human-approved resolution — never a
"merge and continue blindly" resolution.** The grammar is a versioned text artifact; concurrent
edits are reconciled with git-style 3-way merge that **surfaces** conflicts for review rather than
auto-resolving them. This matches the actual workflow (AI proposes, human approves; low
concurrency; expert-driven) and the regime that the CRDT literature itself recommends for
constrained, order-dependent documents.

The CRDT path is reserved for the **lexical tier only** (`lexical/*`), where the data is
MiniLcm-shaped and merges cleanly, and where SIL's own LexBox/Harmony stack already operates.

> A hybrid future (CRDT for the lexical *object bag* + reviewed, atomic operations for ordered
> rule lists) remains open if real-time collaborative grammar editing ever becomes a requirement.
> The typed change-set operations below are deliberately the same primitives that path would need,
> so today's design is not a dead end.

**Non-negotiable safeguard.** Because HC can load a broken grammar without erroring, every
edit/merge/round-trip runs a **validate-and-repair pass** — explicit dangling-reference detection
(including the silently-skipped rule ids) plus a golden-set *parse-and-generate* regression gate.
"It loaded fine" is not evidence of a correct grammar.

### Two-plane architecture

- **Authoring / truth plane (this repo, cross-platform, git-native):** the Hermit Crab ruleset,
  the lexicon, the golden test set, the issue backlog, the change-sets, and the skills. All plain
  files in git. The batch parse-and-flag loop runs here via the Hermit Crab CLI / `SIL.Machine`
  NuGet. The grammar is reconciled by git merge (conflicts surfaced for review); only the lexical
  tier is eligible for CRDT sync.
- **FLEx sync plane (separate effort, Windows):** ingests change-sets into a real FieldWorks
  project. Kept out of this repo to avoid coupling the core loop to Windows / FLEx install /
  project-locking / immature write paths.

## Ecosystem context

| Component | Role | Repo |
|---|---|---|
| FieldWorks / FLEx | Desktop tool linguists use | [sillsdev/FieldWorks](https://github.com/sillsdev/FieldWorks) |
| LibLCM | FieldWorks data model & `.fwdata` storage | [sillsdev/liblcm](https://github.com/sillsdev/liblcm) |
| Hermit Crab | Morphophonological parser + generator (our engine) | [sillsdev/machine](https://github.com/sillsdev/machine) |
| LexBox / Harmony | Cloud sync; lexicon-only CRDT deltas (MiniLcm) | [sillsdev/languageforge-lexbox](https://github.com/sillsdev/languageforge-lexbox) |
| flexlibs / FlexToolsMCP | Python ⇄ LibLCM bridge; an MCP server over FLEx data | [cdfarrow/flexlibs](https://github.com/cdfarrow/flexlibs), [MattGyverLee/FlexToolsMCP](https://github.com/MattGyverLee/FlexToolsMCP) |

## First milestone

A non-interactive, cross-platform spike on one language with existing FLEx data:

1. Export the lexicon and a small interlinear corpus.
2. Generate a Hermit Crab grammar from the current lexicon/rules.
3. Run the corpus through Hermit Crab; collect unparsed words into a structured **issue backlog**
   (with frequency-based impact and a confidence field).
4. Have a skill propose lexeme / allomorph / phonological-rule fixes for the top issues, emitted
   as `morphophonology/*` and `lexical/*` change-set operations.
5. Re-run, gated by the golden `word → gloss` set, and report: failures resolved vs. regressions
   introduced.

If that loop closes — measurably reducing unparsed words without regressions — the rest of the
vision (interactive native-speaker prompts, richer skills, skill promotion) hangs off it.
