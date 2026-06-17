# Natural class

> A set of sounds that pattern together, named either by the features they share or by an explicit
> list — the vocabulary rules and environments are written in.

**LibLCM class:** `PhNaturalClass` (abstract)  ·  **FLEx UI:** "Natural Class" (Grammar area)  ·  **Tier:** morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

A natural class is a group of [[phoneme]]s that behave alike phonologically and can be picked out by a
small set of shared features. "Voiceless stops" {p, t, k} = [−voice, −sonorant, −continuant];
"vowels" = [+syllabic]. Natural classes are what make phonological generalisations *general*: a rule
that voices stops between vowels references the classes "stop" and "vowel" rather than enumerating
every triple. A "class" that needs more features to describe than it contains members is, by the usual
test, *not* natural — a red flag in an analysis.

## How LibLCM models it

`PhNaturalClass` is **abstract** (carrying `Name`, `Abbreviation`, and `Description`), with two
concrete subclasses:
- **`PhNCFeatures`** — defined by a phonological feature structure (`Features`, an owning atomic
  `FsFeatStruc`), e.g. [+voice, −sonorant]. Membership is computed: the model specifies that any
  phoneme which *includes* (note: not merely unifies with) the specified feature values matches.
- **`PhNCSegments`** — defined by an explicit list of `PhPhoneme`s (`Segments`, a *reference*
  collection — `rel card="col"`, not owning, since phonemes are owned by their phoneme set).
  Membership is enumerated.

Both live under the phonology object `PhPhonData` (`NaturalClasses`, an owning sequence).
`PhEnvironment` contexts ([[phonological-environment]]) and phonological-rule structural descriptions
([[phonological-rule]]) reference natural classes — via `PhSimpleContextNC`, whose `FeatureStructure`
attribute points to a `PhNaturalClass`.

## Hermit Crab mapping

HC supports **feature-based** natural classes directly — Maxwell (1998) contrasts the engines exactly
here: AMPLE/XAmple "takes a 'string' view of the world," whereas Hermit Crab "takes a phonetic
feature-based view" with a user-defined feature system. A `PhNCFeatures` exports cleanly to an HC
`NaturalClass` (a `FeatureStruct` over the segment inventory); a `PhNCSegments` exports as an HC class
defined by listing segments (SIL.Machine does have a `SegmentNaturalClass`, so segment lists survive
the round-trip — but feature classes are HC's hallmark). Feature-based classes are preferred because
they stay correct when phonemes are added: a new [+voice, −son] segment automatically joins the class,
whereas a segment list must be edited by hand.

## In our change-sets

```yaml
op: morphophonology.natural_class.create
kind: features                 # features | segments
name: "voiceless_stop"
features: { voice: "-", sonorant: "-", continuant: "-" }
rationale: "Spirantization environment needed a voiceless-stop class; none existed."
confidence: 0.85
impact: { rules_referencing: ["spirantization"] }
```

A `kind: segments` op instead carries a `members: [p, t, k]` list.

## QA & parallel relevance

Checks: **non-natural classes** (segment lists that no feature set captures — flag for review),
**empty/singleton classes**, and **segment-list drift** (a `PhNCSegments` that should have grown when
a phoneme was added). Preferring `PhNCFeatures` over `PhNCSegments` is a standing recommendation the
skills make when proposing rules.

## Pitfalls

- **Segment lists rot.** Adding a [[phoneme]] silently leaves `PhNCSegments` classes stale; feature
  classes self-update.
- **Over-broad feature specs** pull in unintended segments — the mirror image of a stale list.
- A class that isn't *natural* usually signals the rule using it is wrong.

## Related & references

[[phoneme]], [[phonological-environment]], [[phonological-rule]]. — FLEx Phonology docs ("Natural
Classes"); LibLCM `MasterLCModel.xml` (`PhNaturalClass`, `PhNCFeatures`, `PhNCSegments`,
`PhSimpleContextNC`); Maxwell (1998) on HC's feature-based vs AMPLE's string view, Maxwell (2003);
Hayes (2009), SPE (1968). See [../References.md](../References.md).
