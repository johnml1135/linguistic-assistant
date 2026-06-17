# Workflows

One file per **linguistic workflow** this repo assists. Each describes how a human does it in FLEx
today, how the AI assistant supports it (propose / ask-a-speaker / defer), the primitives involved,
and the oracle/metric that gates it.

Cross-link primitives with `[[primitive-name]]`. Cite by author–year / SIL doc name from
[../References.md](../References.md).

## Workflow modes — investigate vs change

Every workflow has a **mode**, the distinction practitioners draw between *"see if this works /
investigate this"* and *"change this from here to there"*:

- **investigate** — read-only: report, audit, check, measure. Output = a report and **review flags**
  into the backlog. No change-set. (Maps to the **scan** loop stage.)
- **change** — mutates the data. Output = **change-set ops** (`lexical/*`, `morphophonology/*`).
  (Maps to **propose + gate**.)
- **mixed** — investigate that may hand off to an optional change (e.g. detect duplicates → propose a
  merge).

This taxonomy is native to the FieldWorks tooling: **FlexTools** modules carry an `FTM_ModifiesDB`
flag (report-only vs DB-modifying) and stage changes through a preview (the *FTFlags* custom field);
**FlexToolsMCP** enforces a mandatory **dry-run (`write_enabled=False`) → write** two-phase guard
(`if modifyAllowed:`); **flexlibs** opens projects with `writeEnabled`. The repo mirrors this safety
discipline with one move: **our change-set IS the preview** — a reviewable text artifact approved
before any ingestion. Investigate workflows never emit a change-set; they emit flags.

> Downstream-write caveat (from the flexlibs survey): the lexicon has a full programmatic write path,
> but morphology/phonology does **not** — flexlibs can create compound/phonological rules and
> templates yet has no path for MSA-type conversion, inflection-class slots, or natural-class
> creation, and most writes are transaction-unprotected. So some `morphophonology/*` changes can only
> be applied by hand in FLEx; workflows flag that rather than implying an auto-fix.

## File template

```markdown
# <Workflow name>

> One-sentence goal.

**Primary tool(s):** …  ·  **Mode:** investigate | change | mixed  ·  **Stage in our loop:** scan | propose | review | gate  ·  **Parallel-aware:** yes / no

## Goal & when it runs
## The human process (in FLEx today)
Concrete step-by-step of how a linguist/team does this now.

## How the assistant supports it
What the skill proposes, when it asks a native speaker vs defers, and what it emits
(`lexical/*` / `morphophonology/*` ops, or review flags into the backlog).

## Inputs
Data required (lexicon, corpus, parallel text, grammar, …).

## Primitives involved
`[[lexical-entry]]`, `[[sense]]`, …

## Oracle / gold / metrics
Deterministic Hermit Crab `word→gloss` golden set and/or parallel-QA eval (precision/recall on flags).

## Outputs
## Pitfalls
## References
```

## Index

### Investigate (read-only: report / audit / check / measure)
- [corpus-coverage-and-frequency](corpus-coverage-and-frequency.md) — parser coverage %, rank unparsed, incomplete analyses; builds the prioritized backlog
- [lexicon-consistency-audit](lexicon-consistency-audit.md) — missing fields, duplicates, inconsistent values → flags
- [data-integrity-check](data-integrity-check.md) — dangling refs, orphan MSAs, count mismatch, HC silent-skip; the validate-and-repair scan/gate

### Mixed (investigate → optional change)
- [duplicate-detection-and-merge](duplicate-detection-and-merge.md) — find duplicate entries/senses, then propose reviewed merges

### Change (emits change-set ops)
- [morphological-parser-setup](morphological-parser-setup.md) — define affixes/allomorphs/rules so HC parses
- [lexeme-and-lexicon-building](lexeme-and-lexicon-building.md) — create/promote entries, senses, allomorphs
- [sense-discovery-and-disambiguation](sense-discovery-and-disambiguation.md) — split/merge senses; choose sense in context
- [bulk-field-standardization](bulk-field-standardization.md) — apply one normalization across many entries, previewed
- [semantic-domain-elicitation-rwc](semantic-domain-elicitation-rwc.md) — Rapid Word Collection

### Cross-cutting (span investigate + change)
- [interlinearization](interlinearization.md) — gloss texts; the parser-in-the-loop *(exemplar)*
- [spell-checking-and-wordform-validity](spell-checking-and-wordform-validity.md) — HC generate-mode validity checking
- [dictionary-publishing](dictionary-publishing.md) — configured views, Webonary, Word/PDF (review before publish)
- [grammar-sketch](grammar-sketch.md) — auto-generated word-level grammar overview
- [parallel-translation-qa](parallel-translation-qa.md) — missing-concept / wrong-sense / agreement checks against the parallel source
