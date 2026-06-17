# Inflection class

> A subdivision of a part of speech whose members inflect the same way — conjugations and declensions —
> used to constrain which affixes attach to which stems.

**LibLCM class:** `MoInflClass`  ·  **FLEx UI:** "Inflection Class"  ·  **Tier:** morphology/phonology
·  **In MiniLcm:** no

## What it is (linguistics)

Within one [[part-of-speech]], words often split into classes that take different inflectional shapes:
Latin's five noun declensions and four verb conjugations; Spanish *-ar / -er / -ir* verbs; Bantu noun
classes (genders) each with their own concord and plural prefixes. Membership is largely arbitrary
(lexically stipulated) — *cantar* and *comer* are both verbs but take different endings purely because
they belong to different conjugations. Inflection classes are how a grammar says "this affix only goes
with that kind of stem."

## How LibLCM models it

`MoInflClass` is owned under a [[part-of-speech]] via `PartOfSpeech.InflectionClasses` (an owning
collection), and classes can nest via `MoInflClass.Subclasses` (also owning) *(verified)*. Fields:
`Name`, `Abbreviation`, `Description`. A `PartOfSpeech` may name a `DefaultInflectionClass`, used when
a stem leaves its class unspecified. The model treats class membership as an essentially arbitrary
lexical label, not something derivable from a stem's allomorph set — which is why it is stipulated, not
computed.

A stem declares its class on `MoStemMsa.InflectionClass`; a derivational affix may set input/output
classes via `MoDerivAffMsa.FromInflectionClass`/`ToInflectionClass`. Importantly, **inflectional-affix
class membership is *not* on the MSA** — an inflectional affix's eligible classes are stored on its
allomorph, `MoAffixForm.InflectionClasses` (defined on the abstract `MoAffixForm` base, so inherited by
both `MoAffixAllomorph` and `MoAffixProcess`). *(Verified: `MoInflAffMsa` has no `InflectionClasses`
field.)* See [[morphosyntactic-analysis]].

## Hermit Crab mapping

Inflection classes become HC features/exception markers that gate affix application: an affix process
applies only when the stem carries the matching class feature. This is HC's mechanism for "regular but
class-specific" morphology, distinct from true irregularity ([[allomorph]] selection or
[[ad-hoc-rule]]s). These class diacritics are HC's stem/MPR-style exception features (require/prohibit
checks), a separate mechanism from the recursive unification of syntactic head [[inflection-feature]]s.

## In our change-sets

Class membership and affix-to-class links are `morphophonology/*` edits:

```yaml
op: morphophonology.inflclass.assign
entry: "comer"
part_of_speech: verb
inflection_class: "er-conjugation"
rationale: "comer takes -emos/-éis endings, not -amos/-áis; it is an -er verb."
confidence: 0.88
```

Defining a new class is a structural op owned under the relevant POS.

## QA & parallel relevance

Wrong-class assignment is a high-yield silent error: the stem still parses, but with the wrong endings,
so generated forms are subtly ungrammatical. Class checks surface in the golden-set
([[interlinearization]] regression) and in parallel-QA when a target inflects a borrowed/derived stem
with the wrong conjugation.

## Pitfalls

- **Putting class on the affix MSA** instead of the affix allomorph — the field does not exist there.
- **Confusing class (arbitrary, lexical) with feature (semantic, e.g. tense)** — see
  [[inflection-feature]].
- **Over-splitting classes** when a single [[phonological-rule]] would explain the surface difference.

## Related & references

[[part-of-speech]], [[morphosyntactic-analysis]], [[inflection-feature]], [[affix-template-and-slot]],
[[allomorph]]. — FLEx Grammar docs; LibLCM `MasterLCModel.xml` (`MoInflClass`); Lockwood (2011) Gilaki
worked example; Maxwell (2003). See [../References.md](../References.md).
