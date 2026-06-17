# Duplicate detection and merge

> Find candidate duplicate entries/senses (investigate), then propose merges as reviewed change-set
> ops (change). The canonical *investigate-then-change* pair.

**Primary tool(s):** FLEx; FlexTools *Find Duplicate Entries/Definitions* → *Merge Entries/Senses*
·  **Mode:** mixed (investigate → change)  ·  **Stage in our loop:** scan + propose + review  ·
**Parallel-aware:** no

## Goal & when it runs

Lexicons accrete duplicates — especially after [[semantic-domain-elicitation-rwc|Rapid Word
Collection]], where the same word is elicited under several domains. This workflow detects them and
consolidates them. It is the clearest example of the two **modes** working together: an
**investigate** pass surfaces candidates; a separate, reviewed **change** pass merges only what a
human approves. Distinct from [[sense-discovery-and-disambiguation]]: that workflow makes the
lump-vs-split *judgment* on a word's meanings; this one consolidates entries/senses already judged to
be the **same** (duplicate headwords, repeated definitions).

## The human process (in FLEx today)

FlexTools encodes this as an explicit two-step, staged through a custom field (**FTFlags**):
1. *Find Duplicate Entries* tags candidates in the **FTFlags** field (matching headword +
   [[morph-type]] + [[part-of-speech]]); *Find Duplicate Definitions* flags entries whose [[sense]]s
   repeat the same definition.
2. A human edits the FTFlags tags (`mt` merge-target, `m`/`md` merge-into, `del` delete), then
   *Merge Entries* / *Merge Senses* executes per the tags (*Merge Senses* collapses senses sharing
   gloss/definition + grammatical category, later merged into earlier). The tag-then-execute split is
   the FlexTools "preview, then apply" discipline (its `FTM_ModifiesDB` flag gates the change step).

## How the assistant supports it

- **Detect** candidates (also semantic near-duplicates the string match misses) and present each as
  *"are these the same? merge / keep separate / ask a speaker."*
- **Propose** approved merges as `lexical/*` merge ops carrying rationale/confidence/impact/provenance.
  **Our change-set is the "preview"**: a reviewable text artifact, the externalized analogue of
  FlexTools' FTFlags staging / FlexToolsMCP's dry-run.

## Inputs

The lexicon (entries, senses, glosses, definitions, POS, homograph numbers); optionally the corpus
to confirm two forms really mean the same thing in use.

## Primitives involved

[[lexical-entry]], [[homograph-number]], [[sense]], [[part-of-speech]], [[lexical-relation]],
[[variant-form]] (some "duplicates" are really variants).

## Oracle / gold / metrics

Detection: parallel-QA-style precision/recall against an annotated duplicate set. The merge op must
be **lossless** — no senses/examples/relations silently dropped — checked before commit.

## Outputs

Investigate: duplicate-candidate flags. Change: reviewed `lexical/*` merge ops.

## Pitfalls

- **Merges are hard to undo** (FLEx has no easy lexicon-merge undo; FlexTools warns to back up). Keep
  merges human-approved and lossless; never auto-merge.
- **Homographs and variants are not duplicates** — distinguish [[homograph-number]] and
  [[variant-form]] cases from true duplicates.
- Keep the modes separate: detection emits flags; merging emits a change-set only after review.

## References

FlexTools Duplicates modules (Find/Merge, FTFlags staging); FLEx merge docs; Atkins & Rundell (2008)
on sense splitting/lumping. See [../References.md](../References.md).
