# Morphosyntactic analysis (MSA)

> The grammatical "wiring" attached to a sense/allomorph that says what category a morpheme is and how
> it combines — the interface between the lexicon and the grammar.

**LibLCM class:** `MoMorphSynAnalysis` (abstract) → `MoStemMsa`, `MoInflAffMsa`, `MoDerivAffMsa`,
`MoUnclassifiedAffixMsa`  ·  **FLEx UI:** "Grammatical Info." / "Category"  ·  **Tier:**
morphology/phonology  ·  **In MiniLcm:** partial

## What it is (linguistics)

A morpheme's *form* (spelling/pronunciation) is separate from its *grammatical behaviour*. The MSA
carries the behaviour: a stem's [[part-of-speech]] and [[inflection-class]]; an affix's category and
which features it realizes; whether an affix is inflectional or derivational. The [[part-of-speech]] it
holds is required morphosyntax the parser acts on — it gates attachment — not the sentence-level syntax
held out of scope here. Two senses of one entry can have different MSAs (a word that is both a noun and
a verb). The MSA is what the parser consults to decide whether *-ed* may attach to *walk* and what the
result's category is.

## How LibLCM models it

MSAs are owned by a [[lexical-entry]] and referenced by each [[sense]]. The four concrete subclasses
*(property names verified against `MasterLCModel.xml`)*:

- **`MoStemMsa`** — for roots/stems: `PartOfSpeech`, `InflectionClass`, `MsFeatures` (an `FsFeatStruc`,
  see [[inflection-feature]]), `ProdRestrict`, `Stratum`, plus `FromPartsOfSpeech` and `Slots` (both
  clitic-only — the categories a clitic attaches to, and the template slots it occupies) *(verified)*.
- **`MoInflAffMsa`** — inflectional affixes: `PartOfSpeech` (the category it attaches within;
  From-POS = To-POS), `InflFeats` (an `FsFeatStruc` of the features it realizes), `Slots` (the
  [[affix-template-and-slot]]s it fills), `FromProdRestrict`, `AffixCategory`. *(There is **no**
  `InflectionClasses` property here — affix inflection-class membership lives on the allomorph,
  `MoAffixForm.InflectionClasses`. Verified against `MasterLCModel.xml`.)*
- **`MoDerivAffMsa`** — derivational affixes, with paired From/To slots so the affix can change a
  stem's grammar: `FromPartOfSpeech`/`ToPartOfSpeech` (may differ),
  `FromInflectionClass`/`ToInflectionClass`, `FromMsFeatures`/`ToMsFeatures`,
  `FromProdRestrict`/`ToProdRestrict`, `FromStemName`, `Stratum`, `AffixCategory` *(verified)*.
- **`MoUnclassifiedAffixMsa`** — an affix with only a `PartOfSpeech`; behaviour not yet specified
  *(verified — `PartOfSpeech` is its sole linguistic property)*.

## Hermit Crab mapping

The MSA is most of what becomes an HC **affix process** or constrains an HC **lexical entry**.
`MoInflAffMsa` features become the head/realized features HC unifies when the affix applies inside its
slot; `MoDerivAffMsa`'s From/To categories become the input/output category change of the process.
`MoStemMsa.PartOfSpeech`/`InflectionClass` constrain which affixes the stem can host. Getting MSAs
right is the difference between a grammar that parses and one that over- or under-generates.

## In our change-sets

MSA edits are `morphophonology/*` ops because they govern combination:

```yaml
op: morphophonology.msa.set
entry: "-i"
msa: { kind: infl_affix, part_of_speech: verb, infl_feats: { tense: past }, slots: [tense-slot] }
rationale: "-i marks past on verbs; inflectional (POS unchanged), fills the tense slot."
confidence: 0.77
```

## QA & parallel relevance

MSA mismatches drive feature/agreement checks: a [[inflection-feature]] an affix realizes must unify
with the stem's features. In parallel-QA, a target word whose MSA cannot realize the
grammatical category present in the source (e.g. no past-tense affix attaches) is a coverage gap; see
[[parallel-translation-qa]].

## Pitfalls

- **Unclassified MSAs** are placeholders — leaving them blocks parsing; flag for completion.
- **Inflectional vs derivational mis-assignment** corrupts category logic; see
  [[inflection-vs-derivation]].
- **Putting inflection class on the wrong object** — for affixes it is the allomorph, not the MSA.

## Related & references

[[part-of-speech]], [[inflection-class]], [[inflection-feature]], [[affix-template-and-slot]],
[[inflection-vs-derivation]], [[lexical-entry]], [[allomorph]]. — FLEx Grammar docs; LibLCM
`MasterLCModel.xml`; Maxwell (1998) on affixes-as-processes. See [../References.md](../References.md).
