# Morphological parser setup

> Define the roots, affixes, allomorphs, classes, and rules a Hermit Crab grammar needs so it can
> segment and gloss words — then iterate against the words it still cannot parse.

**Primary tool(s):** FLEx (Grammar area) + the Hermit Crab parser  ·  **Mode:** change  ·  **Stage in our loop:**
propose + gate  ·  **Parallel-aware:** indirect (a working parser is what makes parallel glossing
checkable)

## Goal & when it runs

A morphological parser only works once the grammar describes the language's morphology and
morphophonology. This workflow is the up-front and ongoing build-out: declaring [[morph-type|roots and
affixes]] with their [[morphosyntactic-analysis|MSAs]], their [[allomorph]]s and environments,
[[natural-class]]es, [[phonological-rule]]s, [[inflection-feature]]s, [[affix-template-and-slot]]s, and
[[ad-hoc-rule]]s. It runs before serious [[interlinearization]] and re-runs every time interlinearizing
surfaces words the parser misses.

## The human process (in FLEx today)

1. In the **Grammar** area, define [[part-of-speech]] categories, [[inflection-feature]]s, and
   [[inflection-class]]es.
2. Enter lexical/affix entries with their [[allomorph]]s and the [[phonological-environment]]s that
   select each one.
3. Build [[natural-class]]es (by feature or segment) and ordered [[phonological-rule]]s; arrange
   inflectional affixes into [[affix-template-and-slot]]s.
4. Add [[ad-hoc-rule]]s to block co-occurrences the general rules wrongly allow.
5. Test with **"Try a Word"** *(exact UI label unverified)*: type a wordform, run the parser, inspect
   the analyses (or the failure trace). Re-parse a text; the list of **unparsed words** drives the
   next round of refinement.

## How the assistant supports it

- **Rank** the highest-frequency unparsed wordforms and, for each, **propose** a minimal fix — a new
  [[allomorph]] + environment, a [[phonological-rule]] tweak, a missing [[affix-template-and-slot]]
  filler, or a relaxed [[ad-hoc-rule]] — with rationale, confidence, and corpus impact.
- Decide the [[natural-class]]es a rule generalizes over with [[../skills/triangulate-phonology]]
  (same-sound vs contrast, from orthographic distribution first and optional phone evidence second),
  then collapse allomorphy with [[../skills/generalize-not-enumerate]].
- Decide **guess now / ask a native speaker / defer**: phonologically ambiguous environments and
  allomorphy-vs-allophony calls are flagged for a speaker rather than guessed.
- **Emit** `morphophonology/*` ops (rule, natural-class, environment, template edits); each is gated by
  the golden set before it lands.

## Inputs

The current Hermit Crab grammar and lexicon, the corpus with its current unparsed-word list, the
phoneme/[[natural-class]] inventory, and prior approved analyses.

## Primitives involved

[[allomorph]], [[natural-class]], [[phonological-rule]], [[phonological-environment]],
[[inflection-feature]], [[affix-template-and-slot]], [[ad-hoc-rule]], [[morphosyntactic-analysis]],
[[stratum]].

## Oracle / gold / metrics

- **Deterministic gate:** the Hermit Crab `word→gloss` **golden set** — every proposed grammar edit
  must still parse *and* generate all known words to their known analyses, with **zero regressions**.
- **Coverage metric:** unparsed-word rate on the corpus (secondary — never traded for a regression).

## Outputs

An expanded, regression-clean grammar; `morphophonology/*` change-set ops with provenance; backlog
flags for environment/allomorphy questions needing a speaker.

## Pitfalls

- **Allomorph environment complexity**: over-broad environments parse the target word but break others
  — exactly what the golden set catches.
- **Allomorphy vs allophony**: a surface alternation may belong in a [[phonological-rule]], not as a
  separate listed [[allomorph]]; choosing wrong bloats the lexicon or hides generality.
- **Silent feature-mismatch failures**: an [[inflection-feature]] clash yields *no parse* with no loud
  error — read the failure trace, don't just see "0 analyses."
- **Slow re-parse loop**: full re-parse is costly; prefer "Try a Word" on representative items, then a
  gated full run.

## References

FLEx Grammar/parser docs and "A Conceptual Introduction to Morphological Parsing" (Black & Simons
2006); Maxwell (2003) *Hermit Crab* and Maxwell (1994) on reversing ordered rules; Lockwood (2011)
Gilaki worked example. See [../References.md](../References.md).
