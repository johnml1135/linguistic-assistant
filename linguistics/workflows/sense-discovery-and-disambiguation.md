# Sense discovery and disambiguation

> Decide how a word's meanings divide into senses, and pick the right sense in a given context — the
> lexicographic judgment a rule-based parser cannot make.

**Primary tool(s):** FLEx (Lexicon Edit) + Texts & Words  ·  **Mode:** change  ·  **Stage in our loop:** propose + review
·  **Parallel-aware:** yes (source-side sense distinctions can reveal missing target senses)

## Goal & when it runs

Once entries exist (see [[lexeme-and-lexicon-building]]), their meaning must be structured: splitting an
over-broad [[sense]] into distinct senses, merging redundant ones, choosing the contextually correct
sense during glossing, and assigning [[semantic-domain]]s. It runs throughout
[[interlinearization]] and during lexicon cleanup.

## The human process (in FLEx today)

1. In **Lexicon Edit**, add, reorder, or nest [[sense]]s and subsenses, each with gloss, definition,
   and [[semantic-domain]].
2. Use **"Merge sense into…"** *(exact UI label unverified)* to collapse a redundant sense, or split
   one entry's sense into two — or split a [[homograph-number|homograph]] into two distinct entries.
3. During glossing, when a wordform has several senses the linguist **selects** the one that fits the
   sentence; the choice is cached on the analysis.

## How the assistant supports it

- **Propose splits/merges** with evidence: distinct collocations or contexts argue for a split;
  overlapping glosses/domains argue for a merge — phrased so a **non-linguist native speaker** can
  confirm ("does this word mean two different things here, or the same thing?").
- **Select sense in context** during glossing (the judgment a parser lacks), citing the disambiguating
  cues, and decide **guess now / ask a speaker / defer**.
- **Parallel angle:** a distinction the source language draws (and our parallel data shows) can
  **suggest a missing target sense** — fed to [[parallel-translation-qa]] as a candidate flag.
- **Emit** `lexical/*` sense ops; merges/splits are tagged high-impact and routed to review.

## Inputs

The lexicon's current sense structure, the corpus with usage contexts, [[semantic-domain]] inventory,
and — for the parallel angle — aligned source text with its senses.

## Primitives involved

[[sense]], [[lexical-entry]], [[homograph-number]], [[semantic-domain]], [[example-sentence]],
[[part-of-speech]].

## Oracle / gold / metrics

- **Parallel-QA:** precision/recall of context sense-selection against annotated examples, and accept
  rate of proposed splits/merges.
- **Deterministic:** sense edits rarely touch the `word→gloss` golden set directly, but glosses linked
  to renamed/merged senses are checked for dangling references.

## Outputs

A cleaner sense hierarchy (splits, merges, domain assignments); per-occurrence sense selections;
backlog flags for boundary calls and candidate missing target senses.

## Pitfalls

- **Sense-boundary fuzziness**: lumping vs splitting has no single right answer — lean on usage
  evidence and Atkins & Rundell's criteria, not intuition alone.
- **Merge/split is hard to undo**: a merge discards structure; treat it as high-impact and prefer a
  reviewed change-set over an in-place edit.
- **RWC polysemy explosion**: rapid collection can spray a word across many domains as separate senses;
  consolidate before they ossify.

## References

Atkins & Rundell (2008) *Oxford Guide to Practical Lexicography* (sense division); Svensén (2009);
FLEx "Merge sense / homographs" docs; Moe RWC for the [[semantic-domain]] side. See
[../References.md](../References.md).
