# Etymology

> The recorded historical origin of an entry — its source form, source language, and gloss — used to
> document loanwords and reconstructed/inherited forms.

**LibLCM class:** `LexEtymology`  ·  **FLEx UI:** "Etymology"  ·  **Tier:** lexical
·  **In MiniLcm:** partial

## What it is (linguistics)

Etymology states where a lexeme came from: the donor word in another language (a loanword, e.g. Swahili
*shule* ← German *Schule* 'school'), or an inherited/reconstructed ancestor. For field lexicography it
is mostly **loanword tracking** — flagging that a vernacular entry is borrowed, from which contact
language, and with what original form and meaning. This both documents language history and warns the
analyst that the form may not obey native [[phoneme]] inventory or morphology.

An etymology is not a [[variant-form]] (a synchronic alternate of the same lexeme) and not a
[[lexical-relation]] (a sense-to-sense semantic link); it is a *diachronic* annotation on a single
[[lexical-entry]].

## How LibLCM models it

`LexEtymology` is an **owning sequence** on `LexEntry` (`LexEntry.Etymology`, card="seq") — an entry can
carry more than one etymology (e.g. competing or layered sources). Fields (verified against
`MasterLCModel.xml`, class 113 — note all string fields are `MultiString`):

- **`Form`** (`MultiString`) — the source/etymon form, per [[writing-system]].
- **`Gloss`** (`MultiString`) — meaning of the source form.
- **`Language`** (reference **sequence** → `CmPossibility`) — the source language(s), chosen from the
  Languages possibility list (owned by `LexDb`). This is FLEx's structured "Source Language" field; it
  is a *sequence*, so a layered loan can cite more than one language.
- **`LanguageNotes`** (`MultiString`) — free-text notes *about* the source language (FLEx UI: "Source
  Language Notes"). This, not `Language`, is where free-typed source descriptions go.
- **`PrecComment`** (`MultiString`) — a preceding comment shown before the etymology.
- **`Comment`** (`MultiString`) — a following/general comment.
- **`Note`** (`MultiString`) — lexicographer's note; appears in the UI but not in dictionary
  configurations (not printed).
- **`Bibliography`** (`MultiString`) — bibliographic source (not printed).

Forms/glosses are per-WS like all multilingual fields. The **"Source"** the prompt asks about is *not*
a single field: FLEx splits it into the structured `Language` reference ("Source Language") and the
free-text `LanguageNotes` ("Source Language Notes"). There is no standalone `Source` field on
`LexEtymology` (the old LIFT free-text source maps onto `LanguageNotes`/`LiftResidue`).

## Hermit Crab mapping

Etymology has **no role** in a Hermit Crab grammar — it is pure documentation, not parsing data. It is
worth noting only because loanwords often justify a separate [[stratum]] or relaxed phonotactics
(borrowed segments outside the native inventory), so an etymology can *motivate* a grammar change even
though it is never encoded in HC itself.

## In our change-sets

```yaml
op: lexical.etymology.create
entry: "entry:shule"
language: ["Swahili"]               # Language: ref-seq into the Languages list
language_notes: { en: "via coastal Swahili trade contact" }
source_form: { sw: "shule" }        # LexEtymology.Form
gloss: { en: "school" }
note: "Borrowed via coastal trade; not a native stem."
rationale: "Loanword origin documented for QA of irregular phonology."
confidence: 0.85
```

Ops carry rationale/confidence/impact/provenance like all `lexical/*` edits.

## QA & parallel relevance

In [[parallel-translation-qa]], an etymology helps explain why a key term is borrowed rather than
coined, and supports consistency checks on transliterated proper nouns. In
[[lexeme-and-lexicon-building]] the assistant may *propose* (never assert) a loanword etymology when a
form matches a contact-language word — always low-confidence and flagged for human review.

## Pitfalls

- **Etymology ≠ synchronic source.** A loan's source form is not a parseable [[allomorph]]; do not feed
  it to HC.
- **Folk etymology / speculation.** Proposed origins are easy to over-assert; keep confidence low and
  cite.
- **Language list drift.** `Language` points at the Languages possibility list; stuffing the language
  name into free-text `LanguageNotes` instead fragments the data and defeats grouping by source.

## Related & references

[[lexical-entry]], [[writing-system]], [[phoneme]], [[stratum]], [[variant-form]]. — FLEx Lexicon docs
(Etymology fields); LibLCM `MasterLCModel.xml` (`LexEtymology`); LIFT format. See
[../References.md](../References.md).
