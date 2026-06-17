# Primitives

One file per **morphological or lexical idea expressible in LibLCM** — the atoms our change-sets edit
and our skills reason about. Each file maps the concept across four planes: linguistics → LibLCM class
→ Hermit Crab → our change-set ops, plus its QA/parallel relevance.

Filenames are kebab-case. Cross-link freely with `[[other-primitive]]`. Cite sources by author–year or
SIL doc name, defined in [../References.md](../References.md).

## File template

```markdown
# <Primitive name>

> One-sentence definition.

**LibLCM class:** `<ClassName>`  ·  **FLEx UI:** "<name>"  ·  **Tier:** lexical | morphology/phonology
·  **In MiniLcm:** yes / no / partial

## What it is (linguistics)
Plain-language linguistic explanation, with a cross-linguistic example or two.

## How LibLCM models it
The class(es), key fields, and ownership/reference relationships. Be precise about class names;
verify against MasterLCModel.xml / FLEx docs. Note the FLEx-UI name.

## Hermit Crab mapping
How this surfaces (or does not) in a Hermit Crab grammar; any round-trip (parse/generate) note.

## In our change-sets
Which `lexical/*` or `morphophonology/*` operation expresses an edit to this concept; a tiny example
op; reminder that ops carry rationale/confidence/impact/provenance.

## QA & parallel relevance
How this shows up in checks (missing sense, agreement/feature mismatch, validity/spell-check, …),
including the parallel-source angle where relevant.

## Pitfalls
Gotchas, silent-failure modes, common confusions.

## Related & references
`[[related-primitive]]` links + key works from References.md.
```

## Index

### Lexical
- [lexical-entry](lexical-entry.md) — `LexEntry`; lexeme form vs citation form *(exemplar)*
- [homograph-number](homograph-number.md) — `LexEntry.HomographNumber`
- [sense](sense.md) — `LexSense`; gloss vs definition; subsenses
- [example-sentence](example-sentence.md) — `LexExampleSentence` + `CmTranslation`
- [allomorph](allomorph.md) — `MoForm` / `MoStemAllomorph` / `MoAffixAllomorph`
- [part-of-speech](part-of-speech.md) — `PartOfSpeech` (via MSA)
- [semantic-domain](semantic-domain.md) — `CmSemanticDomain`; RWC
- [lexical-relation](lexical-relation.md) — `LexReference` / `LexRefType`
- [cross-lingual-sense-link](cross-lingual-sense-link.md) — bilingual tier: vernacular sense ↔ reference lemma (FLExTrans sense link; Apertium bidix source)
- [complex-form](complex-form.md) — `LexEntryRef` / `LexEntryType` (compounds, derivatives, idioms)
- [variant-form](variant-form.md) — `LexEntryRef` variant types
- [etymology](etymology.md) — `LexEtymology`
- [pronunciation](pronunciation.md) — `LexPronunciation`
- [reversal-index-entry](reversal-index-entry.md) — `ReversalIndexEntry`
- [writing-system](writing-system.md) — `CoreWritingSystemDefinition`; vernacular vs analysis

### Morphology / phonology
- [morph-type](morph-type.md) — `MoMorphType` (root, stem, prefix, suffix, infix, circumfix, clitic, …)
- [morphosyntactic-analysis](morphosyntactic-analysis.md) — MSA family: `MoStemMsa`, `MoInflAffMsa`, `MoDerivAffMsa`, `MoUnclassifiedAffixMsa`
- [inflection-vs-derivation](inflection-vs-derivation.md) — the distinction as LibLCM/FLEx encodes it
- [inflection-class](inflection-class.md) — `MoInflClass`
- [affix-template-and-slot](affix-template-and-slot.md) — `MoInflAffixTemplate` / `MoInflAffixSlot`
- [inflection-feature](inflection-feature.md) — `FsFeatureSystem` / `FsFeatStruc` / closed & complex features
- [phoneme](phoneme.md) — `PhPhoneme`, phoneme set, segments as feature bundles
- [natural-class](natural-class.md) — `PhNaturalClass` (`PhNCFeatures` vs `PhNCSegments`)
- [phonological-environment](phonological-environment.md) — `PhEnvironment`
- [phonological-rule](phonological-rule.md) — `PhRegularRule`, `PhMetathesisRule`
- [compound-rule](compound-rule.md) — `MoCompoundRule` (`MoEndoCompound` / `MoExoCompound`)
- [ad-hoc-rule](ad-hoc-rule.md) — `MoAdhocProhib` (`MoAlloAdhocProhib` / `MoMorphAdhocProhib`)
- [productivity-restriction](productivity-restriction.md) — exception features / `ProdRestrict`
- [stratum](stratum.md) — `MoStratum` + Hermit Crab strata & rule ordering
