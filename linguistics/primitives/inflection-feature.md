# Inflection feature

> The grammatical features (tense, number, gender, case, person…) and their values that morphemes carry
> and that must agree when morphemes combine — checked by feature unification.

**LibLCM class:** `FsFeatureSystem` + `FsFeatStruc`; `FsClosedFeature`/`FsSymFeatVal`,
`FsComplexFeature`  ·  **FLEx UI:** "Feature System" / "Inflection Features"  ·  **Tier:**
morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

Grammatical behaviour is described with **features**: *number* = {sg, pl}, *tense* = {pres, past},
*person* = {1, 2, 3}, *gender*, *case*. A morpheme either *realizes* a value (the suffix *-s* realizes
number = pl) or *requires* one. When morphemes combine, their features must be compatible —
**agreement** is feature matching (a 3sg subject prefix with a 3sg verb form). Bundles like
person+number are often handled together as one complex feature (an agreement bundle).

## How LibLCM models it

The language's inventory lives in `FsFeatureSystem`, which owns the feature definitions (`Features`,
a collection of `FsFeatDefn`) and the structure types (`Types`, a collection of `FsFeatStrucType`). An
actual assignment of values is an `FsFeatStruc` *(verified spelling — **not** `FsFeatureStructure`)*,
which owns its value specifications (`FeatureSpecs`) and references a `Type`; it is used as
`MoStemMsa.MsFeatures`, `MoInflAffMsa.InflFeats`, the From/To feature slots of `MoDerivAffMsa`, and a
template's `Region` (see [[morphosyntactic-analysis]], [[affix-template-and-slot]]). Feature
definitions descend from the abstract base `FsFeatDefn`:

- **`FsClosedFeature`** — a closed set of symbolic values; its `Values` are `FsSymFeatVal`s (e.g.
  number ∈ {sg, pl}). *(verified)*
- **`FsComplexFeature`** — a feature whose value is itself an `FsFeatStruc` (its `Type` references an
  `FsFeatStrucType`), i.e. nested features such as an *agreement* feature bundling person and number.
  *(verified)*
- **`FsOpenFeature`** — a feature whose value is open (string/writing-system valued) rather than drawn
  from a fixed symbolic set. *(verified)*

*(There is no concrete `FsFeatureDefn`; `FsFeatDefn` is abstract, with the closed/open/complex
subclasses above.)*

## Hermit Crab mapping

These are HC's **head and rule features**, resolved by **feature unification**: when an affix process
applies, the features it specifies must unify with the stem's features, or the combination fails.
Closed features become symbolic feature values; complex features become nested feature structures HC
unifies recursively. This is the mechanism behind agreement and paradigm-cell selection in HC, and a
prime source of *correct-looking-but-wrong* parses when a value is mis-set.

## In our change-sets

Feature inventory and per-morpheme feature assignments are `morphophonology/*` ops:

```yaml
op: morphophonology.feature.assign
entry: "-s"
infl_feats: { number: pl }
rationale: "-s realizes plural number on nouns; needed for noun-NUM agreement checks."
confidence: 0.86
```

Defining a new closed/complex feature is a structural op on the feature system.

## QA & parallel relevance

Features power agreement checks — the core of grammatical QA, and the agreement signal
[[parallel-translation-qa]] depends on. A subject–verb or noun–adjective feature mismatch is flagged
directly; in parallel work, a target clause whose features cannot unify with the agreement the source
implies (e.g. a plural subject paired with a singular verb form) is exactly the discrepancy that
workflow surfaces. Missing values in the inventory cause silent under-checking: with nothing to
compare, no error fires even though the form is wrong.

## Pitfalls

- **Spelling/casing** — the class is `FsFeatStruc`; getting the model name wrong breaks tooling.
- **Closed vs complex** — flatten an agreement bundle into separate closed features and you lose the
  unit that should unify together.
- **Feature vs [[inflection-class]]** — features are semantic/grammatical; classes are arbitrary
  lexical groupings; don't encode one as the other.

## Related & references

[[morphosyntactic-analysis]], [[part-of-speech]], [[inflection-class]], [[parallel-translation-qa]].
— FLEx Grammar docs; LibLCM `MasterLCModel.xml` (`FsFeatureSystem`, `FsFeatStruc`, `FsClosedFeature`,
`FsComplexFeature`); Maxwell (1998) on head vs rule features; GOLD feature ontology. See
[../References.md](../References.md).
