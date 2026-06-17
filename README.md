# Linguistic Assistant

An AI assistant for field linguists working with **FieldWorks** / **LibLCM** data.

> **Status: research / exploration.** This repo is an early-stage investigation, not a
> production tool. Scope, formats, and architecture are still being shaped.

## What it is

Field linguists and Bible-translation teams use SIL
[FieldWorks Language Explorer (FLEx)](https://software.sil.org/fieldworks/) to build dictionaries and
morphological analyses of (usually low-resource) languages, and to check translated texts. FLEx
already runs a parser-in-the-loop: a morphological parser proposes analyses of words, and a trained
linguist approves or rejects them, word by word.

This project is an AI **quality-assurance and language-documentation assistant** for that work — it
is **not** a translation system. (Translation itself is done separately by a fine-tuned **NLLB-200**
encoder-decoder model — SIL's [Serval](https://ai.sil.org/projects/serval) stack; this tool *checks*
the translations that process produces and *documents* the language behind them.) The goal is an AI
layer that:

- **Proposes** lexical entries, senses, and morphophonological rules from corpus **and parallel-text**
  evidence, rather than just running a fixed parser.
- **Checks translations and documentation against parallel data** — e.g. *"this parallel data
  suggests this word is missing a sense,"* or *"this word is singular in the source but plural here —
  is that correct?"*
- Works through a **batch backlog of issues** (unparsed words, conflicting analyses, parallel-derived
  flags) prioritized by confidence and impact, instead of grinding word-by-word in a UI.
- Makes contribution **accessible** — surfacing decisions a *non-linguist native speaker* can
  answer ("which of these three readings is right?"), not only ones requiring a trained linguist.
- Knows when to **guess, ask, or defer**: "I know enough to make a good guess" vs. "present
  options to a speaker" vs. "not enough data, move on."

The differentiator over pure rule-based parsing is this **judgment layer** (implemented as Claude
skills), not the parser itself.

## Scope

The product is **quality assurance + language documentation**: enriching the lexicon, validating and
glossing wordforms, and reviewing translated text against parallel sources. The virtuous cycle is
**Bible-translation teams working through highly parallel literature** (the New Testament and similar).

**In scope:**

- **Lexicon QA and enrichment** — senses, entries, examples, POS, semantic domains; sense/concept
  coverage checks. *(The largest share of the work — see the breakdown below.)*
- **Morphology & phonology** via Hermit Crab — interlinearization, lexeme/allomorph discovery,
  morphophonological rule proposal, and **validity / spell-checking** (Hermit Crab *generate* mode).
- **Parallel-aware checking** — first-class from v1: missing-sense detection, sense-correctness, and
  feature/agreement checks (e.g. number/agreement mismatches).

**Out of scope:**

- **Generating translations / machine translation.** That is the separate fine-tuned NLLB-200 model;
  we never produce target text, and we do **not** build Apertium or transfer rules. (FLExTrans /
  Apertium were evaluated and ruled out for exactly this reason.)
- **Free-standing syntactic rule induction.** We only auto-propose rules where a generative **engine
  + a regression oracle** both exist (morphology: Hermit Crab + golden `word → gloss` set).
  Cross-word and agreement checks borrow the **gold structure of the aligned source** (well-analyzed
  parallel literature) rather than inducing a syntactic grammar we cannot verify. Note: the
  morphosyntax the parser *requires* — POS, inflection class, features, affix templates — **is** in
  scope; only sentence-syntax *induction* is out.

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

Change-sets are tiered, because the SIL ecosystem treats these data differently:

| Tier | Covers | Notes |
|---|---|---|
| `lexical/*` | entries, senses, examples, parts of speech, semantic domains | Shaped to mirror **MiniLcm** (the model behind [LexBox](https://github.com/sillsdev/languageforge-lexbox) / Harmony CRDT sync), so the ingestion effort *can* lower them onto that path later. |
| `morphophonology/*` | phonological rules, natural classes, allomorph environments, affix templates, inflection classes/features, strata | **Our own schema**, expressed against Hermit Crab grammar constructs. No structured delta format for this exists upstream — LexBox/Harmony deltas are lexicon-only. |
| `bilingual/*` | cross-lingual **sense links** (vernacular sense ↔ reference-language lemma) | The alignment substrate for parallel-translation QA. Primary, reviewable source; an Apertium **bidix** (`.dix`) is *derived* from it (FLExTrans-compatible). **Input to QA, not MT** — no transfer rules. See `research/bilingual/`. |

Every operation carries **rationale, confidence, impact, and provenance** (a link back to the corpus
or **parallel-text** evidence that triggered it), so the whole change-set is reviewable as plain text
in git. Review *flags* (e.g. "missing sense here") feed the issue backlog; the *fixes* are change-set
operations.

### Parallel data and two kinds of gold set

Aligned **parallel text** — a translated corpus against its source, typically the New Testament and
similar highly parallel literature — is a **first-class input from v1**, not a later add-on. The
highest-value checks are parallel-driven (*"this suggests a missing sense"; "singular in the source,
plural here — correct?"*), and they exploit the fact that the source side of such literature has
**gold morphology and known grammatical relations** — so agreement/structure checks reduce to
comparing target features against a known backbone rather than inducing syntax.

Consequently, evaluation (and LLM/skill optimization) is measured against **two kinds of gold set**:

| Gold set | Used for | Nature | Metric |
|---|---|---|---|
| **Monolingual** `word → gloss` (Hermit Crab) | morphophonology rule changes | deterministic engine output | regressions — parses/generations broken vs. fixed |
| **Parallel QA** (annotated aligned examples) | parallel-driven checks (missing sense, agreement, sense-correctness) | LLM judgment | precision / recall on correctly-flagged issues |

The deterministic gate is a hard pass/fail; the parallel-QA eval is a scored benchmark the research
playground iterates against.

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

> The two-plane split is about **data ownership**. Two further axes — code *maturity* and *runtime*
> — are described next; don't conflate them. Full detail in
> [`docs/superpowers/specs/2026-06-16-runtime-and-staging-architecture-design.md`](docs/superpowers/specs/2026-06-16-runtime-and-staging-architecture-design.md).

## Runtime & maturity architecture

### Where the LLM runs — offline review, online proposal

The differentiator is the judgment/skills layer, which wants a *frontier* LLM — but many users are
**offline for weeks**, and the small models that run offline are weakest at exactly the
morphology/agreement reasoning this project needs. So **the LLM is not co-located with the user.**
The loop is split so the *only* step needing connectivity is the creative proposal:

- **Offline half** (field laptop, no GPU): HC parse → backlog, human review of proposals, apply
  approved deltas, the golden-set regression gate, git history. Hermit Crab is managed .NET and needs
  no GPU, so **the oracle and the safety gate never depend on the cloud.**
- **Online half** (wherever compute is): skills + RAG generate change-set *proposals* via a
  **swappable endpoint** — a `Microsoft.Extensions.AI` `IChatClient`. Shipped default is a
  **SIL-hosted** open model (Serval-style, keeps a community's data in SIL's trust boundary);
  **BYOK-frontier** is the opt-in connected mode. Data egress is explicit, visible config — not an
  accident of which endpoint is set.

### Three maturity stages (this repo holds 1 and 2)

1. **Research playground — Python (`research/`).** Where ideas iterate (prompts/skills, RAG,
   evaluation). An idea is *proven* when it reliably emits valid change-sets that pass the golden gate.
2. **Validation program — C#/.NET 10 (`src/`).** Builds/validates HC rules, makes the LLM calls,
   runs the parser, produces/applies change-sets, and ships a **sample UI** (the loop console below).
   *Proven* when the loop closes measurably — fewer unparsed words, no golden-set regressions.
3. **Product split-off (downstream).** The proven C# **core** becomes a NuGet package or migrates
   into an official product (FieldWorks, **FieldWorks Lite**, or **Paratext 10**). The sample UI is
   **throwaway**; only the engine libraries migrate.

Stage boundaries are **promotion gates**, not folders. The cross-stage contracts are the
**change-set schema** (stage 1 emits it, stage 2 validates/applies it, downstream ingests it) and
**portable skills** (markdown + tool contracts — promoted from research as data, not rewritten).

### Slice 1 — the local "loop console"

A single **`net10.0`** process (`dotnet run`) serving a thin web UI at `localhost` (browser/webview —
the FwLite pattern). It drives one end-to-end cycle — **parse → propose → review → gate → commit** —
where everything is local and offline except the single proposal call. First user: the
linguist-developer, proving the loop on one language.

The core is three UI-free, individually packable libraries targeting `net10.0` (so a future FwLite
panel or Paratext plugin can reference them in-process); the web host is a deliberately disposable
consumer of them:

| Project | Role |
|---|---|
| `SIL.LinguisticAssistant.HermitCrab` | parse → backlog; golden-set parse **and** generate; dangling-ref/strata checks |
| `SIL.LinguisticAssistant.ChangeSets` | change-set schema; validate · apply · validate-and-repair |
| `SIL.LinguisticAssistant.Proposer` | backlog + RAG + portable skill → change-set ops, via an injected `IChatClient` |
| `SIL.LinguisticAssistant.Console` *(host)* | minimal-API + thin web UI; orchestrates the three — **throwaway** |

## Ecosystem context

| Component | Role | Repo |
|---|---|---|
| FieldWorks / FLEx | Desktop tool linguists use | [sillsdev/FieldWorks](https://github.com/sillsdev/FieldWorks) |
| LibLCM | FieldWorks data model & `.fwdata` storage | [sillsdev/liblcm](https://github.com/sillsdev/liblcm) |
| Hermit Crab | Morphophonological parser + generator (our engine) | [sillsdev/machine](https://github.com/sillsdev/machine) |
| LexBox / Harmony | Cloud sync; lexicon-only CRDT deltas (MiniLcm) | [sillsdev/languageforge-lexbox](https://github.com/sillsdev/languageforge-lexbox) |
| flexlibs / FlexToolsMCP | Python ⇄ LibLCM bridge; an MCP server over FLEx data | [cdfarrow/flexlibs](https://github.com/cdfarrow/flexlibs), [MattGyverLee/FlexToolsMCP](https://github.com/MattGyverLee/FlexToolsMCP) |

## First milestone

**Slice 1 — the loop console** (see the runtime/staging design above): a `net10.0` app that drives
one end-to-end cycle on one language with existing FLEx data **and aligned parallel text**,
everything local except the proposal call:

1. Export the lexicon, a small interlinear corpus, and **an aligned parallel text** (source ↔ target)
   — a stage-1/input step, outside the core loop.
2. Generate a Hermit Crab grammar from the current lexicon/rules.
3. Build the **issue backlog** from two sources: (a) words Hermit Crab fails to parse; (b)
   **parallel-derived flags** (e.g. missing sense, number/agreement mismatch) — each with
   frequency-based impact and a confidence field.
4. Have a skill propose fixes for the top issues — the single online call — emitted as `lexical/*`
   and `morphophonology/*` change-set operations (e.g. add a sense, fix an allomorph) for review.
5. Apply approved ops and re-run, gated by **both** the deterministic golden `word → gloss` set
   (regressions) and the **parallel-QA eval** (precision/recall on flags); report results; commit to
   git or revert.

If that loop closes — measurably improving the lexicon/parse and catching real translation issues
without regressions — the pipeline is proven (stage 2→3), and the rest of the vision (job-queue sync
for offline batch, interactive native-speaker prompts, richer checks, skill promotion, embedding into
FwLite/Paratext) hangs off it.

## References

LingGym - https://github.com/changbingY/LingGym - https://arxiv.org/html/2511.00343v1

FieldWorks Lite - https://github.com/sillsdev/languageforge-lexbox

LibLCM - 