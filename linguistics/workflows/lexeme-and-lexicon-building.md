# Lexeme and lexicon building

> Grow the dictionary from texts and word collections — creating and promoting lexical entries, senses,
> and allomorphs — while keeping duplicates and bare wordforms out.

**Primary tool(s):** FLEx (Lexicon area) + Texts & Words  ·  **Mode:** change  ·  **Stage in our loop:** scan + propose +
review  ·  **Parallel-aware:** indirect (a fuller lexicon improves both parsing and parallel-QA recall)

## Goal & when it runs

A parser is only as good as its lexicon. This workflow creates [[lexical-entry|lexical entries]], their
[[sense]]s and [[allomorph]]s, and promotes recurrent unanalyzed wordforms into real entries. It runs
continuously alongside [[interlinearization]] (entries minted on the fly during glossing) and in bulk
after [[semantic-domain-elicitation-rwc|RWC]] imports.

## The human process (in FLEx today)

1. In **Lexicon Edit**, create an entry: lexeme form, [[part-of-speech]] (via [[morphosyntactic-analysis|MSA]]),
   one or more [[sense]]s with gloss/definition, and any [[allomorph]]s.
2. FLEx surfaces existing entries with the same form (the **"Similar entries" / Find Entry** check
   *(exact UI labels unverified)*) to avoid duplicates before saving.
3. From **Texts & Words**, the linguist **promotes** a wordform (right-click → create entry) so future
   occurrences parse, and the parser caches the analysis.
4. Bulk edits and the **Bulk Edit Wordforms** tools batch-apply category, gloss, or status across many
   wordforms.

## How the assistant supports it

- **Propose entries** for the most frequent recurrent unparsed wordforms, pre-filling lexeme form,
  candidate [[part-of-speech]], a draft [[sense]]/gloss (from corpus context and, when present, an
  aligned source gloss), each tagged with **provenance and confidence**.
- **Flag likely duplicates** before creation by matching form, gloss, and [[homograph-number]] against
  the lexicon — and propose **merge** rather than a new entry where appropriate.
- Decide **guess now / ask a native speaker / defer** for thin or uncertain entries; **emit**
  `lexical/*` ops (new entry / sense / allomorph) and review flags.

## Inputs

The corpus and its unparsed/recurrent-wordform list, the current lexicon, any aligned source glosses,
and RWC/LIFT imports awaiting cleanup.

## Primitives involved

[[lexical-entry]], [[sense]], [[allomorph]], [[part-of-speech]], [[morphosyntactic-analysis]],
[[homograph-number]], [[morph-type]], [[semantic-domain]].

## Oracle / gold / metrics

- **Deterministic:** new entries/allomorphs must not regress the Hermit Crab `word→gloss` **golden
  set** (a new [[allomorph]] can wrongly capture other words).
- **Parallel-QA:** precision/recall of proposed entries (accepted vs rejected) and of duplicate flags.

## Outputs

New and expanded [[lexical-entry|entries]], [[sense]]s, and [[allomorph]]s with provenance; merged
duplicates; backlog flags for entries needing speaker confirmation or richer metadata.

## Pitfalls

- **Entry-vs-wordform confusion**: promoting every inflected wordform as its own entry instead of as an
  analysis of an existing lexeme; promote the **lexeme**, let the parser handle inflection.
- **Duplicate proliferation**: skipping the similar-entries check spawns near-identical entries that
  fragment senses and parses.
- **Sparse metadata from RWC**: rapid-collection entries often arrive with a gloss but no definition,
  POS, or examples — flag thin entries for follow-up rather than treating them as complete.

## References

FLEx "Lexicon Edit / Find Entry" docs; LIFT interchange format; Atkins & Rundell (2008) on entry
structure; Moe RWC methodology and The Combine for the import side. See [../References.md](../References.md).
