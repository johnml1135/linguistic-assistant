# Complex form

> A lexical entry whose meaning/form is built from two or more other entries — a compound, derivative,
> idiom, phrase, or saying — recorded as a reference from the whole to its parts.

**LibLCM class:** `LexEntryRef` (RefType = complex form)  ·  **FLEx UI:** "Complex Form" / "Components"
·  **Tier:** lexical  ·  **In MiniLcm:** partial

## What it is (linguistics)

A complex form is a [[lexical-entry]] that is *composed of* other entries. English *blackbird* is a
compound of *black* + *bird*; *unhappiness* is a derivative built on *happy*; *kick the bucket* is an
idiom whose meaning is not the sum of *kick*, *the*, *bucket*. FLEx groups these as **complex-form
types**: compound, derivative, idiom, phrase, saying (and an "unspecified" default). The defining trait
is that the complex form *points back at* its component entries/senses, so a reader (or the parser) can
trace the whole to its parts.

This is the headword-level analogue of a [[compound-rule]]: the rule is the productive
morphophonological machinery; the complex form is the *stored, lexicalized* result that earns its own
dictionary entry (often because its meaning is non-compositional).

## How LibLCM models it

A complex form is **not** a separate class — it is a `LexEntryRef` owned in `LexEntry.EntryRefs`, with
`RefType` flagging it as a complex form (vs a [[variant-form]], same class, other flag). Key fields:

- **`ComponentLexemes`** — reference sequence to the component `LexEntry`/`LexSense` objects (the parts:
  *kick*, *the*, *bucket*).
- **`PrimaryLexemes`** — a *subset* of `ComponentLexemes`; the components the complex form is shown
  *under* as a subentry in a root-based dictionary (drives placement). Unused for variants.
- **`ComplexEntryTypes`** — reference sequence of `LexEntryType` (a `CmPossibility` subclass) giving the
  type(s): compound, derivative, etc. (`VariantEntryTypes` is its sibling, unused for complex forms.)
- **`ShowComplexFormsIn`** — reference sequence (subset of `ComponentLexemes`) controlling which
  referenced entries list this item as a complex form in a stem-based dictionary.
- **`HideMinorEntry`** — `Integer` (default 0); whether it appears as a minor entry in publication.

The complex-form entry owns its own `LexemeForm` and [[sense]]s like any entry; the `LexEntryRef` just
records the composition. **`RefType` is a plain `Integer` enum on `LexEntryRef`** (0 = variant,
1 = complex form), *not* a typed reference — it is a discriminator used by the UI to decide whether the
ref displays as a variant or a complex form. The *types themselves* live in the separate
`ComplexEntryTypes` / `VariantEntryTypes` reference collections (each pointing at `LexEntryType`
possibility items). Verified against `MasterLCModel.xml` (class 127, `RefType` `sig="Integer"`).

## Hermit Crab mapping

Lexicalized complex forms are usually entered into Hermit Crab as ordinary stem [[lexical-entry]]s
(stored wholes), so the parser recognizes *blackbird* directly rather than re-deriving it. Productive
composition is handled instead by [[compound-rule]]s over the components. Idioms/phrases that exceed the
word boundary fall outside HC's word-level scope and are documentation-only.

## In our change-sets

```yaml
op: lexical.complex_form.create
entry: { lexeme_form: { seh: "nyumba-imbwa" } }
complex_type: compound
components: ["entry:nyumba", "entry:imbwa"]
primary: ["entry:nyumba"]
rationale: "Recurs as a fixed compound; non-compositional 'kennel' sense."
confidence: 0.66
provenance: { corpus: "mark", refs: ["MRK 5:3"] }
```

Ops carry rationale/confidence/impact/provenance like all `lexical/*` edits.

## QA & parallel relevance

[[parallel-translation-qa]] uses complex forms to catch a source idiom rendered word-for-word in the
target (likely a missing idiom entry), or a compound that should be one entry but appears as loose
words. [[lexeme-and-lexicon-building]] proposes a complex form when an unparsed token decomposes into
known entries but recurs as a fixed unit.

## Pitfalls

- **Compound entry vs [[compound-rule]].** Storing a productive compound as a fixed entry hides the
  rule; encoding a lexicalized idiom as a rule over-generates. Pick by (non-)compositionality.
- **Complex form vs [[variant-form]].** Same `LexEntryRef` class — only the type flag differs. A
  variant references *one* main entry; a complex form references *multiple* components.
- **Empty `PrimaryLexemes`** leaves the entry unplaced in publication (silent omission).

## Related & references

[[lexical-entry]], [[sense]], [[variant-form]], [[compound-rule]], [[part-of-speech]]. — FLEx Lexicon
docs ("About Complex Forms"); LibLCM `MasterLCModel.xml` (`LexEntryRef`); Haspelmath & Sims (2010) on
compounding/derivation. See [../References.md](../References.md).
