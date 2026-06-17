# Lexical entry

> The top-level dictionary record for a lexeme or morpheme — the container that owns its forms,
> senses, and grammatical information.

**LibLCM class:** `LexEntry`  ·  **FLEx UI:** "Entry" / "Headword"  ·  **Tier:** lexical  ·  **In MiniLcm:** yes

## What it is (linguistics)

A lexical entry is the unit a dictionary is built from: one lexeme (e.g. *walk*) or bound morpheme
(e.g. the plural suffix *-s*). It is *not* the same as a wordform — a single entry underlies many
inflected surface forms (*walk, walks, walked, walking*). An entry bundles everything known about that
lexeme: how it is written, what it means (its [[sense]]s), what shapes it takes (its [[allomorph]]s),
and how it behaves grammatically (its [[part-of-speech]] and [[morphosyntactic-analysis]]).

Two "forms" of an entry are easy to confuse:
- **Lexeme form** — the underlying form used in analysis and as the basis for parsing (e.g. the root).
- **Citation form** — the headword as conventionally cited in the dictionary (e.g. an infinitive
  *marcher* even though the lexeme form is the stem *march-*). If no citation form is set, FLEx falls
  back to the lexeme form.

## How LibLCM models it

`LexEntry` owns:
- **`LexemeForm`** — a `MoForm` (the default [[allomorph]]); its `MorphType` ([[morph-type]]) says
  whether the entry is a root, stem, prefix, etc.
- **`CitationForm`** — a multilingual string used as the headword when present.
- **`Senses`** — an owning sequence of [[sense]] (`LexSense`); the first is the primary sense.
- **`AlternateForms`** — an owning sequence of `MoForm`: additional [[allomorph]]s beyond the lexeme form.
- **`Pronunciations`** (owning seq of `LexPronunciation`, [[pronunciation]]), **`Etymology`** (owning
  seq of `LexEtymology`, [[etymology]]), **`EntryRefs`** (an owning sequence of `LexEntryRef`,
  used for [[complex-form]]s and [[variant-form]]s).
- **`HomographNumber`** ([[homograph-number]]) — a `basic` Integer (0–255; `0` = none shown) that
  disambiguates same-spelled entries; FLEx auto-renumbers it, so it is *not* a stable id.

Entries are owned in the lexical database (`LexDb`; surfaced as the `LexDb.Entries` collection).
Forms are stored per [[writing-system]] (vernacular for the form, analysis for glosses/definitions).

## Hermit Crab mapping

A `LexEntry` whose morph type is a root/stem becomes a Hermit Crab **lexical entry** (an underlying
lexeme with a single underlying form + its allomorphs). Affix entries become HC **affix processes**
([[morphosyntactic-analysis]] carries the category/feature info HC needs). The citation/lexeme-form
distinction matters: HC parses and generates over the *lexeme* (underlying) form, not the citation form.

## In our change-sets

Edits to an entry are `lexical/*` operations shaped to mirror MiniLcm, e.g.:

```yaml
op: lexical.entry.create
lexeme_form: { seh: "kufamba" }      # vernacular writing system
morph_type: stem
rationale: "Unparsed wordform 'kufamba' recurs 14× in corpus; no entry covers the stem."
confidence: 0.72
impact: { unparsed_tokens_affected: 14 }
provenance: { corpus: "mark", refs: ["MRK 1:16", "MRK 2:14"] }
```

Adding senses/allomorphs/pronunciations are separate ops owned-under this entry.

## QA & parallel relevance

Most workflows touch entries: [[lexeme-and-lexicon-building]] creates them from unparsed words;
[[interlinearization]] links morphemes to them; [[parallel-translation-qa]] may flag that a source
concept has **no entry/sense** in the target lexicon ("missing-sense"). Getting the lexeme-vs-citation
form right is a recurring data-quality check.

## Pitfalls

- **Entry ≠ wordform.** Promoting every inflected surface form to its own entry corrupts the lexicon;
  inflected forms belong to *one* entry with [[allomorph]]s/MSAs.
- **Citation-form drift.** A citation form that isn't a real generable form breaks round-trip checks.
- **Premature homograph splits** vs genuine [[homograph-number]] cases — see [[sense]] for the
  split-vs-new-entry decision.

## Related & references

[[sense]], [[allomorph]], [[morph-type]], [[part-of-speech]], [[homograph-number]],
[[complex-form]], [[variant-form]]. — FLEx Lexicon docs; LibLCM `MasterLCModel.xml`; Atkins & Rundell
(2008) on entry structure. See [../References.md](../References.md).
