# Reversal index entry

> An entry in a reverse (gloss → headword) index for one analysis language: a word in the analysis
> language pointing at the vernacular senses it translates.

**LibLCM class:** `ReversalIndexEntry`  ·  **FLEx UI:** "Reversal Entry" / "Reversal Indexes"
·  **Tier:** lexical  ·  **In MiniLcm:** partial

## What it is (linguistics)

A normal dictionary is vernacular → meaning. A **reversal index** runs the other way: given an
analysis-language word (say English *water*), it lists the vernacular [[sense]]s that mean it. This is
what lets a speaker of the analysis language *find* a vernacular word from its gloss — the back-of-book
"English–Vernacular" finder list. Because a project may publish reversals for several metalanguages,
each language gets its own index, and each indexed word is one reversal index entry.

It is built *from* senses, not authored independently: the linguist tags a [[sense]] with the reversal
words it should appear under, and FLEx assembles the index.

## How LibLCM models it

`ReversalIndexEntry` is owned by `ReversalIndex` (one index per analysis language). `ReversalIndex`
(class 52) owns its `Entries` (a collection of `ReversalIndexEntry`), a `PartsOfSpeech` possibility
list, and a `WritingSystem` (`Unicode` — the BCP-47 tag the index is for). Fields on
`ReversalIndexEntry` (verified against `MasterLCModel.xml`, class 53):

- **`ReversalForm`** (`MultiUnicode`) — the analysis-language word being indexed (primary form in the
  index's writing system).
- **`Senses`** (reference **sequence** → `LexSense`) — the vernacular senses this word indexes. The
  current model carries this as a direct `Senses` reference on the reversal entry, so the relationship
  is sense ⇄ reversal entry. *(The "directly" wording is what the model now shows; earlier FLEx
  versions reached it via a back-reference from the sense — exact version of the change unverified, so
  treat the directionality, not the date, as the load-bearing fact.)*
- **`PartOfSpeech`** (atomic ref → `PartOfSpeech`) — POS in the analysis language, to disambiguate
  (e.g. *fly* noun vs verb). (Drawn from the index's own `PartsOfSpeech` list, not the vernacular POS
  list.)
- **`Subentries`** (owning **sequence** → `ReversalIndexEntry`) — nested entries, so reversals can be
  hierarchical (a head reversal word with sub-reversals).

Because `Senses` is a reference, the same vernacular sense can surface under many reversal forms, and a
reversal form can gather many senses.

## Hermit Crab mapping

None — reversal indexes are a **publishing/lookup** artifact, not parsing data. HC neither produces nor
consumes them. They are listed here because they are first-class lexical objects our change-sets and
QA touch.

## In our change-sets

```yaml
op: lexical.reversal_entry.create
index_language: "en"
reversal_form: { en: "water" }
part_of_speech: "noun"
senses: ["sense:madzi#1"]
rationale: "Sense 'madzi (water)' had no English reversal; finder-list gap."
confidence: 0.9
```

Ops carry rationale/confidence/impact/provenance like all `lexical/*` edits.

## QA & parallel relevance

Reversal coverage is a documentation-completeness metric the assistant can report on for
[[dictionary-publishing]]: senses with no reversal entry are invisible in the finder list. In
[[parallel-translation-qa]], the reversal index is a quick way to ask "does the lexicon already have a
word for this source concept?" — a missing reversal often co-occurs with a missing [[sense]].

## Pitfalls

- **Reversal ≠ translation.** A reversal form is a *finder key*, not an asserted equivalence; over-rich
  reversals bloat the index and blur sense distinctions.
- **POS omission** collapses homographous reversal words (*fly* n./v.) into one confusing entry.
- **Stale references.** Deleting/merging a [[sense]] can leave a reversal entry pointing at nothing —
  a silent broken finder link.

## Related & references

[[sense]], [[lexical-entry]], [[part-of-speech]], [[writing-system]], [[dictionary-publishing]]. —
FLEx Lexicon/Reversal docs; LibLCM `MasterLCModel.xml` (`ReversalIndexEntry`, `ReversalIndex`). See
[../References.md](../References.md).
