# Interlinearization

> Break a text into segments → words → morphemes and attach a lexical entry + gloss to each, producing
> morpheme-by-morpheme glossed text — the core annotated artifact of language documentation.

**Primary tool(s):** FLEx (Texts & Words / Analyze) + the morphological parser  ·  **Mode:** mixed  ·  **Stage in our
loop:** scan + propose + review  ·  **Parallel-aware:** yes (the baseline text is often one side of a
parallel pair)

## Goal & when it runs

Interlinearization turns raw text into structured data: every word is segmented into [[morph-type|morphemes]],
each morpheme linked to a [[lexical-entry]] and given a [[sense]]/gloss, with [[part-of-speech]] and a
free translation. It is the dominant day-to-day activity that *both* feeds the lexicon and exercises
the morphology, so it is where most QA value is created.

## The human process (in FLEx today)

1. Import/enter the **baseline** text; FLEx segments it into sentences and words.
2. In **Analyze**, for each word the **parser** (Hermit Crab, in our case) proposes one or more
   morpheme breakdowns with candidate entries/glosses.
3. The linguist **approves/edits/rejects** a parse; approved analyses are cached and auto-applied to
   later identical wordforms ("approved" wordforms).
4. Unparseable words are segmented and linked **by hand**, often creating a new [[lexical-entry]] or
   [[allomorph]] on the fly — which feeds [[lexeme-and-lexicon-building]] and
   [[morphological-parser-setup]].
5. The result follows the **Leipzig Glossing Rules** (baseline / word / morphemes / gloss / category /
   free translation tiers).

## How the assistant supports it

- **Propose** analyses for unparsed words, drawing on corpus frequency, existing lexicon, and (when
  available) the aligned source gloss — and decide *guess now / ask a native speaker / defer*.
- **Disambiguate sense in context**: where a wordform has several [[sense]]s, propose the contextually
  right one (the LLM judgment a pure parser lacks), phrased so a non-linguist can confirm.
- **Emit** results as `lexical/*` ops (new entry/sense/allomorph) and approved-analysis records; open
  questions become review **flags** in the backlog.

## Inputs

Baseline text (ideally interlinear-ready), the current lexicon and Hermit Crab grammar, prior approved
analyses, and — for parallel-aware glossing — the aligned source text and its gloss.

## Primitives involved

[[lexical-entry]], [[allomorph]], [[sense]], [[part-of-speech]], [[morph-type]],
[[morphosyntactic-analysis]], [[phonological-rule]] (when surface forms diverge from underlying).

## Oracle / gold / metrics

- **Deterministic:** the Hermit Crab `word→gloss` **golden set** — does the grammar still parse known
  words to their known analyses (parse *and* generate), with no regressions?
- **Parallel-QA:** for context-sense choices, precision/recall against annotated examples.

## Outputs

Glossed interlinear text; new/expanded lexicon entries and senses; a growing set of approved
wordform analyses; backlog flags for words that need a human decision.

## Pitfalls

- **Editing the baseline breaks existing analyses** — re-interlinearization is costly; treat the
  approved-analysis set as state to preserve.
- **Silently-wrong parses**: an ill-ordered [[phonological-rule]] can yield a plausible but wrong
  analysis (not a failure) — hence the golden-set regression gate, not just "did the unparsed count drop."
- **Sense over-selection**: don't mint a new [[sense]] when an existing one fits; see
  [[sense-discovery-and-disambiguation]].

## References

FLEx "Interlinearize Texts" and "Parser and interlinear text" (Black, Simons, Zook); Leipzig Glossing
Rules; Maxwell (1994/2003) on HC parse/generate. See [../References.md](../References.md).
