# Part of speech

> The grammatical category of a word (noun, verb, transitive verb …) — morphosyntax the parser
> *requires*, attached to a sense through its MSA.

**LibLCM class:** `PartOfSpeech`  ·  **FLEx UI:** "Category" / "Grammatical Info." (Parts of Speech list)  ·  **Tier:** lexical (bridges to morphology)  ·  **In MiniLcm:** yes

## What it is (linguistics)

A part of speech (POS, "category") is a word's grammatical class: noun, verb, adjective, adposition,
and finer subtypes (transitive vs intransitive verb). Categories form a **hierarchy** — *transitive
verb* is a subcategory of *verb*, inheriting what verbs can do. POS governs what affixes a word takes,
which [[inflection-class]] it may belong to, and which [[inflection-feature]]s it inflects for. **For
this repo the framing is critical:** POS is *morphosyntax the parser needs*, so it is firmly **in
scope** — it is not the sentence-level "syntax" we exclude. Without POS, Hermit Crab cannot decide
which affixes attach.

## How LibLCM models it

`PartOfSpeech` is a `CmPossibility`, so it inherits `Name`, `Abbreviation`, and `SubPossibilities`
(the inheritance hierarchy). The categories live in the **`LangProject.PartsOfSpeech`** possibility
list (the [[reversal-index-entry]]'s `ReversalIndex` owns a separate one). Key morphology-bearing
properties:
- **`InflectionClasses`** — owning collection of [[inflection-class]] (`MoInflClass`) defined on this
  category.
- **`AffixTemplates`** (owning seq of `MoInflAffixTemplate`) / **`AffixSlots`** (owning collection of
  `MoInflAffixSlot`) — the [[affix-template-and-slot]] machinery.
- **`InflectableFeats`** — reference collection of `FsFeatDefn`: the [[inflection-feature]]s a word of
  this category inflects for (the analogous derivation-relevant set is **`BearableFeatures`**, also a
  reference collection of `FsFeatDefn`).
- **`InherFeatVal`** (owned `FsFeatStruc` of inherent feature values), `DefaultInflectionClass`
  (ref to `MoInflClass`), and `StemNames` (owned `MoStemName`s).

Crucially, a [[sense]] does **not** point at a POS directly — it points at a
[[morphosyntactic-analysis]] (MSA), and the MSA carries the POS (`MoStemMsa.PartOfSpeech`, etc.).

## Hermit Crab mapping

POS becomes a Hermit Crab **morphosyntactic category** (a node in HC's category hierarchy with its
inflectional/inherent features). HC uses it to gate affixation: an [[affix-template-and-slot]] is
defined per category, and an affix process states which category it attaches to and outputs. The
hierarchy means an affix specified for *verb* also applies to *transitive verb*.

## In our change-sets

POS edits ride on the MSA. A `lexical/*` op typically sets a sense's MSA category:

```yaml
op: lexical.msa.set_category
sense: "kufamba#1"
part_of_speech: "Verb"
rationale: "Inflects with verbal subject prefixes in corpus; currently miscategorized as noun."
confidence: 0.74
impact: { affixes_now_licensed: ["ku-", "-a"] }
```

Creating a new category is its own op against the PartsOfSpeech list. Ops carry
rationale/confidence/impact/provenance.

## QA & parallel relevance

A wrong or missing POS is a frequent **silent parse failure**: the right affixes are never licensed,
so wordforms go unparsed in [[interlinearization]] with no error. QA checks: senses with no MSA/POS;
POS that contradicts the affixes actually seen in the corpus; and, in [[parallel-translation-qa]], a
target rendering whose category mismatches the source's grammatical role.

## Pitfalls

- **POS is reached via the MSA, not set on the sense directly** — editing the wrong object is a common
  mistake.
- **Over-flat or over-deep hierarchies** make affix licensing wrong; mirror the language's real
  subcategories.
- **Treating POS as out-of-scope "syntax"** — it is morphosyntax the parser depends on; it is in scope.

## Related & references

[[morphosyntactic-analysis]], [[inflection-class]], [[inflection-feature]], [[affix-template-and-slot]],
[[sense]], [[inflection-vs-derivation]]. — FLEx Grammar docs; LibLCM `MasterLCModel.xml`
(`PartOfSpeech`, `LangProject.PartsOfSpeech`); Payne (1997) *Describing Morphosyntax*; GOLD ontology.
See [../References.md](../References.md).
