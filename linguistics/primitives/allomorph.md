# Allomorph

> A surface shape a morpheme takes — *a* vs *an*, English plural /s ~ z ~ ɪz/ — optionally
> conditioned by its phonological environment.

**LibLCM class:** `MoForm` (abstract) → `MoStemAllomorph`, `MoAffixForm` → `MoAffixAllomorph` / `MoAffixProcess`  ·  **FLEx UI:** "Lexeme Form" / "Allomorphs"  ·  **Tier:** lexical / morphology boundary  ·  **In MiniLcm:** partial

## What it is (linguistics)

A single morpheme often surfaces in several phonologically distinct shapes called **allomorphs**.
English *a ~ an* before consonants vs vowels; the plural suffix as /s/ (*cats*), /z/ (*dogs*), /ɪz/
(*horses*); a root that changes shape before certain suffixes. Allomorphy may be **phonologically
conditioned** (predictable from the environment) or **suppletive** (irregular, e.g. *go ~ went*). The
choice is described by a [[phonological-environment]] — often with an "elsewhere" default.

## How LibLCM models it

`MoForm` is the abstract base, with two branches:
- **`MoStemAllomorph`** — allomorph of a root/stem (extends `MoForm` directly).
- **`MoAffixForm`** (abstract) — affix allomorphs, split into **`MoAffixAllomorph`** (the
  Item-and-Arrangement affix allomorph) and **`MoAffixProcess`** (its Item-and-Process sibling, which
  carries `Input`/`Output` rule mappings instead of a listed form).

Shared `MoForm` properties: **`Form`** (`MultiUnicode`, per vernacular [[writing-system]]),
**`MorphType`** (atomic reference to [[morph-type]] / `MoMorphType`), and `IsAbstract`. Conditioning
lives in **`PhoneEnv`** — a **reference collection** of [[phonological-environment]] (`PhEnvironment`)
objects (a collection, to allow several environments before they are collapsed to one; an empty value
= "no restriction / elsewhere"). The entry's **`LexemeForm`** ([[lexical-entry]], atomic) is the
*default* allomorph; additional allomorphs live in `LexEntry.AlternateForms` (an owning sequence).
`MoAffixAllomorph` adds `Position` (for infixes) and morphosyntactic-environment fields.

## Hermit Crab mapping

Here LibLCM and HC diverge. LibLCM can *list* allomorphs explicitly. Hermit Crab prefers a **single
underlying form + ordered [[phonological-rule]]s** that derive the surface shapes (Maxwell 2003) — the
"stealth-to-wealth" endpoint is to reduce a morpheme to one underlying form whose allomorphs fall out
from the rules. So an explicit allomorph set with `PhoneEnv` conditioning maps to HC either as listed
allomorphs *or*, better, as one form plus rules. Round-trip parsing requires that whatever HC derives
matches the attested surface forms.

## In our change-sets

Allomorphs are `lexical/*`; the rules that derive them are `morphophonology/*`:

```yaml
op: lexical.allomorph.create
entry: "-z"            # plural suffix
form: { seh: "es" }
morph_type: suffix
environment: "/ [+sibilant] _"
rationale: "Surface 'es' after sibilants; currently overgenerates 's'."
confidence: 0.6
```

A morphophonology op might instead add a [[phonological-rule]] so HC derives the allomorph. Ops carry
rationale/confidence/impact/provenance.

## QA & parallel relevance

Allomorphy is a top cause of **silent parse failure**: a wordform won't parse because the needed
allomorph/rule is missing, so the token is dropped from [[interlinearization]] with no error. QA
should surface unparsed tokens that differ from a known form only by a predictable alternation — a
strong hint that an allomorph or rule is missing.

## Pitfalls

- **Listing allomorphs that should be rule-derived** bloats the lexicon and hides generalizations;
  prefer a [[phonological-rule]] when the alternation is regular.
- **`PhoneEnv` ordering matters** under disjunctive ("elsewhere") interpretation.
- **Default-allomorph confusion**: the `LexemeForm` *is* an allomorph; don't duplicate it in
  `AlternateForms`.

## Related & references

[[lexical-entry]], [[morph-type]], [[phonological-environment]], [[phonological-rule]],
[[morphosyntactic-analysis]], [[interlinearization]]. — FLEx Grammar/Parsing docs; LibLCM
`MasterLCModel.xml` (`MoForm`, `MoStemAllomorph`, `MoAffixAllomorph`); Maxwell (2003) *Hermit Crab*;
Hayes (2009) on allomorphy. See [../References.md](../References.md).
