# Example sentence

> An attested or illustrative sentence showing a sense in use, together with its translation(s) and a
> source reference.

**LibLCM class:** `LexExampleSentence`  ·  **FLEx UI:** "Example" (under a sense, with "Translation" and "Reference")  ·  **Tier:** lexical  ·  **In MiniLcm:** yes

## What it is (linguistics)

A good dictionary illustrates each [[sense]] with example sentences — they show register,
collocation, argument structure, and disambiguate which reading is meant. Each example is in the
vernacular and is usually accompanied by one or more **translations** (a free translation; sometimes
also a literal one) and a **reference** crediting the source (a corpus citation, a speaker, a text).
For a Scripture-aligned project the reference is typically a verse ID (e.g. MRK 1:16), which makes
examples a natural bridge to [[parallel-translation-qa]].

## How LibLCM models it

`LexExampleSentence` is owned by `LexSense.Examples` (an owning **sequence**). Its properties:
- **`Example`** — `MultiString` (multilingual, formatted): the vernacular sentence. It is a
  *MultiString* (not MultiUnicode) so a word can be bolded and multiple vernacular [[writing-system]]s
  can coexist.
- **`Translations`** — an owning **sequence** of `CmTranslation`. Each `CmTranslation` has a
  **`Translation`** (`MultiString`) and a **`Type`** (atomic reference to a `CmPossibility` —
  the translation-type list: *Free*, *Literal*, *Back*, etc., owned by `LangProject.TranslationTags`).
- **`Reference`** — a `String` naming the text source.

So the shape is: sense → example → (one vernacular form + N typed translations + a reference).

## Hermit Crab mapping

No direct HC object. Examples are documentation, not grammar. They are, however, **gold-test
material**: the vernacular `Example` is exactly the kind of attested string the parser should be able
to interlinearize, so examples feed the parse/round-trip test corpus that gates grammar changes.

## In our change-sets

Adding an example is a `lexical/*` op owned under a sense:

```yaml
op: lexical.example.create
sense: "kufamba#1"
example: { seh: "Iye akafamba kuenda kumusha." }
translations:
  - { type: free, text: { en: "He walked home." } }
reference: "MRK 1:16"
rationale: "Attested use disambiguating the motion sense."
confidence: 0.7
provenance: { corpus: "mark", refs: ["MRK 1:16"] }
```

Ops carry rationale/confidence/impact/provenance.

## QA & parallel relevance

Examples are prime parallel material: the vernacular `Example` plus its free `Translation` form a
mini parallel pair we can check against the source text in [[parallel-translation-qa]] (e.g. does the
example's translation actually use the gloss it illustrates?). A `Reference` that points at a corpus
location lets QA pull the surrounding context. Missing or untyped translations weaken these checks.

## Pitfalls

- **Translation type matters.** A *back* translation is not a *free* translation; mislabeling
  (`Type`) corrupts downstream comparisons.
- **Reference vs translation language** — the `Reference` is metadata, not a translation; don't conflate.
- **Examples that don't parse** are useful QA signals but should be flagged, not silently imported as
  gold tests.

## Related & references

[[sense]], [[lexical-entry]], [[writing-system]], [[parallel-translation-qa]], [[interlinearization]].
— FLEx Lexicon docs; LibLCM `MasterLCModel.xml` (`LexExampleSentence`, `CmTranslation`); Leipzig
Glossing Rules (Comrie et al. 2008). See [../References.md](../References.md).
