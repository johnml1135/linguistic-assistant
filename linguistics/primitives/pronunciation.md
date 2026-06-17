# Pronunciation

> A phonetic/IPA rendering of an entry, optionally with audio recordings and the location where it was
> elicited.

**LibLCM class:** `LexPronunciation`  ·  **FLEx UI:** "Pronunciation"  ·  **Tier:** lexical
·  **In MiniLcm:** partial

## What it is (linguistics)

A pronunciation records *how an entry sounds*, distinct from how it is spelled. For a tone or
non-phonemic orthography this is essential: the headword *kúfa* tells a reader nothing about the high
tone unless a phonetic form (and ideally audio) carries it. An entry may have several pronunciations —
dialectal differences, or simply a man's and a woman's recording of the same word — so the data model
treats pronunciation as a repeatable, media-bearing annotation on a [[lexical-entry]].

Pronunciation is phonetic *surface* data; it is not the underlying [[phoneme]]mic analysis the grammar
parses over, though the two should be consistent.

## How LibLCM models it

`LexPronunciation` is an **owning sequence** on `LexEntry` (`LexEntry.Pronunciations`, card="seq").
Fields (verified against `MasterLCModel.xml`, class 14):

- **`Form`** (`MultiUnicode`) — the pronunciation form (an approximately phonemic/IPA encoding for the
  printed dictionary), stored per [[writing-system]]; typically a **vernacular-phonetic / IPA writing
  system** rather than the practical orthography.
- **`MediaFiles`** (owning **sequence** → `CmMedia`) — the audio recordings; `CmMedia` wraps a `CmFile`
  via its `MediaFile` ref and carries a `Label`, so multiple files (man/woman/dialect) can hang off one
  pronunciation.
- **`Location`** (atomic ref → `CmLocation`) — where the form was recorded/elicited (`CmLocation` is a
  `CmPossibility` subclass, from the Locations list).
- **`CVPattern`** (`String`) — consonant–vowel skeleton.
- **`Tone`** (`String`) — tone marking (e.g. `HL`, `12`). Note both `CVPattern` and `Tone` are single
  `String`s (defaulting to the top analysis WS), **not** multilingual `MultiString`s.

Audio bytes live in the linked `CmFile`; `CmMedia.MediaFile` points to it. The `Form` is per-WS like
every multilingual field; the `CVPattern`/`Tone` strings are not.

## Hermit Crab mapping

Pronunciation is **not** parsing input — HC works over the [[phoneme]]mic underlying form, not a
phonetic transcription or audio. It is documentation. That said, a phonetic `Form` is a useful
*consistency check* on the grammar: if HC's generated surface form disagrees with the recorded
pronunciation, the [[phonological-rule]]s or [[phoneme]] inventory may be wrong.

## In our change-sets

```yaml
op: lexical.pronunciation.create
entry: "entry:kufa"
form: { seh-fonipa: "kúfá" }        # Form: per-WS (vernacular-phonetic / IPA)
tone: "HH"                          # Tone: single String, not per-WS
location: "Sena, Mutarara"          # CmLocation ref
rationale: "Tone unrecoverable from orthography; documented for tone-pair QA."
confidence: 0.8
```

Audio attachment (`CmMedia` → `CmFile`) is a separate op owned under this pronunciation. All `lexical/*`
ops carry rationale/confidence/impact/provenance.

## QA & parallel relevance

In [[parallel-translation-qa]], pronunciations support checks on near-homophones that a translator may
have confused, and on tone minimal pairs. In [[lexeme-and-lexicon-building]] a missing pronunciation on
a tonal-language entry is a documentation-completeness flag, not a parse error.

## Pitfalls

- **Wrong writing system.** Putting IPA in the orthographic [[writing-system]] (or vice versa) corrupts
  sort/search and display.
- **Pronunciation ≠ underlying form.** Feeding a phonetic transcription to HC as a [[phoneme]]mic form
  produces wrong analyses.
- **Orphaned media.** A `CmMedia` whose `CmFile` is missing is a silent broken link in publication.

## Related & references

[[lexical-entry]], [[writing-system]], [[phoneme]], [[phonological-rule]]. — FLEx Lexicon docs
(Pronunciation, media); LibLCM `MasterLCModel.xml` (`LexPronunciation`, `CmMedia`, `CmFile`). See
[../References.md](../References.md).
