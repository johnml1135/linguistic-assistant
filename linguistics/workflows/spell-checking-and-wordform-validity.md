# Spell-checking & Wordform Validity

> Use the morphology to decide whether a surface form is well-formed — parse/generate the wordform and
> flag what the grammar can't account for as a likely typo, missing entry, or over-strict rule.

**Primary tool(s):** FLEx (spelling dictionary + morphological parser) + Hermit Crab generate/parse  ·  **Mode:** mixed  ·
**Stage in our loop:** scan + gate  ·  **Parallel-aware:** partly (validates the target text's forms)

## Goal & when it runs

Two layers stack here. **FLEx's own spell-checking** is a **Hunspell** dictionary: a flat list of
attested vernacular wordforms (the `.dic`/`.aff` files FLEx writes from wordforms marked *Correct*),
which catches forms not yet seen but says nothing about *why* a form is or isn't well-formed. **On top
of that**, this repo adds a **morphology-driven validity** layer: a wordform is "valid" if the Hermit
Crab grammar can account for it — the parser tells us which surface forms it can [[allomorph|segment]]
and [[phonological-rule|derive]], and HC **generate** mode tells us which forms the grammar would
itself produce. These are complementary, not interchangeable: Hunspell is a membership test against
known words; HC-generate is a generativity test against the rules. Forms that fail are surfaced for
triage. This is a cheap, high-volume QA pass that feeds [[interlinearization]] and
[[morphological-parser-setup]].

## The human process (in FLEx today)

1. FLEx maintains a **vernacular spelling dictionary** (Hunspell `.dic`/`.aff` in the user's
   `hunspell` folder); wordforms whose Spelling Status is *Correct* are written to the `.dic` on FLEx
   startup, and "Show Vernacular Spelling Errors" underlines everything not in it.
2. The linguist runs the **parser** over wordforms; unparsed forms accumulate as a worklist.
3. For each flagged form the linguist decides: fix the typo, add a [[lexical-entry]]/[[allomorph]], or
   loosen a rule that wrongly blocked a real word.
4. Generated-but-unattested and attested-but-ungenerable forms both signal grammar/lexicon gaps.

## How the assistant supports it

- **Scan** the corpus, cross-referencing parser results with HC generate output, and **triage** each
  flag into *typo* / *missing lexicon* / *too-strict rule* — the judgment a raw unparsed-count lacks.
- For typos, **propose** the most likely intended form (edit-distance + valid neighbours) and decide
  *fix / ask a native speaker / defer*; for gaps, emit candidate `lexical/*` or `morphophonology/*` ops.
- **Emit** spelling-status updates and a triaged flag backlog; never silently auto-correct vernacular.

## Inputs

The corpus or target draft, the current spelling dictionary, the lexicon, and the Hermit Crab grammar
(both directions). For parallel-aware checks, the aligned source helps confirm a rare form is intended.

## Primitives involved

[[phonological-rule]], [[allomorph]], [[lexical-entry]], [[morph-type]], [[writing-system]].

## Oracle / gold / metrics

- **Deterministic:** the Hermit Crab `word→gloss` golden set — validity logic must not regress known
  good words to "invalid" nor start accepting known-bad forms.
- **Parallel-QA:** precision/recall of typo-vs-gap triage against an annotated sample.

## Outputs

Updated spelling status; candidate lexicon/rule ops for true gaps; a triaged backlog of suspected
typos, missing entries, and over-strict rules.

## Pitfalls

- **Morphologically rich languages** generate many rare-but-valid forms → false-positive typos; weight
  by corpus frequency and the source-side evidence, don't flag on parse-failure alone.
- **Unstandardized orthography** makes "typo" ill-defined; defer to a native speaker rather than impose.
- **Loanwords and proper nouns** legitimately escape the grammar — route to the lexicon, not the typo bin.

## References

FLEx "Spell Checking vernacular words" and "Vernacular spelling dictionary files" (Hunspell);
Maxwell (1994/2003) on HC parse *and* generate. See [../References.md](../References.md).
