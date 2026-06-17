# Homograph number

> The small integer that distinguishes two same-spelled but distinct entries — shown as a
> superscript on the headword (*bank*¹ vs *bank*²).

**LibLCM class:** `LexEntry.HomographNumber`  ·  **FLEx UI:** "Homograph number" (superscript on headword)  ·  **Tier:** lexical  ·  **In MiniLcm:** yes

## What it is (linguistics)

When two lexemes happen to share a written form but are genuinely different words — different
etymologies, unrelated meanings, often different [[part-of-speech]] — a dictionary treats them as
**homographs** and gives each its own [[lexical-entry]]. The homograph number is the disambiguator a
reader sees printed as a superscript: English *bank*¹ ('financial institution') vs *bank*² ('river
edge'); *lie*¹ ('recline') vs *lie*² ('tell an untruth'). It is a *display and identity* device, not a
claim about meaning — distinct meanings of the *same* word are [[sense]]s/subsenses, not homographs.

## How LibLCM models it

`HomographNumber` is a `basic` integer property on `LexEntry` (`sig="Integer"`, `min="0"`,
`max="255"`). A value of `0` means "no homograph number" (the entry is unique by form, so nothing is
shown). When two or more entries share the same homograph form, FLEx assigns `1, 2, 3 …` in order.
The grouping key is the **homograph form** (derived from the [[lexical-entry]]'s lexeme/citation form
plus, in some configurations, the [[morph-type]] and homograph-writing-system), so a prefix *in-* and
a root *in* need not collide. FLEx **auto-manages** the numbering: adding, deleting, or re-spelling an
entry triggers a renumber so the set stays gapless and consistent.

## Hermit Crab mapping

No direct counterpart. Hermit Crab disambiguates lexical entries by internal identity, not by a
human-facing superscript. Homograph number is bookkeeping for the dictionary/UI layer; it carries no
phonological or morphosyntactic content the parser consumes.

## In our change-sets

We rarely set it directly — it is derived. A `lexical/*` op that creates or re-spells an entry should
flag the homograph *consequence* rather than hard-code a number:

```yaml
op: lexical.entry.create
lexeme_form: { seh: "banki" }
note: "Collides with existing 'banki'¹; FLEx will assign homograph 2."
confidence: 0.8
```

Hard-coding a literal `homograph_number` is fragile (see Pitfalls); prefer letting import/FLEx renumber.

## QA & parallel relevance

A homograph cluster is a signal to check: does a [[parallel-translation-qa]] hit for "banki" mean
homograph 1 or 2? Ambiguous headword references in a corpus or back-translation are a real
data-quality risk. Flag entries whose homograph set has grown unexpectedly — often a sign of a
[[sense]] that was wrongly split into a new entry.

## Pitfalls

- **Numbers are not stable IDs.** They renumber as entries are added/removed; never use them as a
  durable key (use the entry GUID).
- **Homograph vs sense confusion.** Related meanings belong under one entry as [[sense]]s; only truly
  distinct lexemes get separate entries with homograph numbers.
- **Hard-coded numbers in change-sets** drift out of sync after a renumber.

## Related & references

[[lexical-entry]], [[sense]], [[part-of-speech]], [[morph-type]], [[writing-system]]. — FLEx Lexicon
docs; LibLCM `MasterLCModel.xml` (`LexEntry.HomographNumber`, Integer 0–255); Atkins & Rundell (2008)
on homograph treatment. See [../References.md](../References.md).
