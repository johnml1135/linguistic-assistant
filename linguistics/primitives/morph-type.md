# Morph type

> The classification of a morpheme/form as root, stem, affix, or clitic — the property that decides
> whether an entry behaves like a stem or like something that attaches to one.

**LibLCM class:** `MoMorphType` (a `CmPossibility`)  ·  **FLEx UI:** "Morpheme Type"  ·  **Tier:**
morphology/phonology  ·  **In MiniLcm:** partial (lexeme-form type is surfaced)

## What it is (linguistics)

Every morpheme has a *type* that says how it combines: a **root** is the lexical core (*walk*); a
**stem** is a root plus any derivation that inflection attaches to; **affixes** (prefix, suffix,
infix, circumfix, simulfix, suprafix) are bound and attach to stems; **clitics** (proclitic,
enclitic) are phonologically bound but syntactically word-like (English *'s*, Romance object
pronouns). **Interfixes** are linking elements between roots in compounds. The type is what tells the
parser that *-s* can never stand alone and that *walk* can.

The full FLEx inventory: **root, bound root, stem, bound stem, particle, phrase, discontiguous
phrase, prefix, suffix, infix, circumfix, prefixing/suffixing/infixing interfix, simulfix, suprafix,
proclitic, enclitic, clitic** *(all 19 verified against `MasterLCModel.xml` + `ConstantAdditions.cs`)*.

Notation in forms uses leading/trailing markers: prefix `mu-`, suffix `-a`, infix `-um-`, circumfix
`ge- -t`, proclitic `na=`, enclitic `=yo`, bound root/stem `*tion`; stems/roots carry no marker.

## How LibLCM models it

`MoMorphType` is a `CmPossibility` (base class verified) living in the project's fixed Morph Types
possibility list *(the list's stable GUID is a liblcm code constant, e.g. `kguidMorphTypes` — not in
`MasterLCModel.xml`; unverified)*. The leading/trailing marker is **data-driven**, not hardcoded per
type: each `MoMorphType` carries **`Prefix`** (leading string, e.g. `-` or `=`), **`Postfix`**
(trailing string), and **`SecondaryOrder`** for sorting homographs of different types — all verified
as `basic` string/integer props. It also owns `Input` and `Output` `FsFeatStruc`s used to contribute
features during attachment *(verified)*. *(The literal default marker glyphs are seeded by the
NewLangProj template, not by liblcm — treat the exact characters as conventional, unverified.)* Every
[[allomorph]] (`MoForm`) references a `MorphType`; a [[lexical-entry]]'s `LexemeForm.MorphType` is what
makes the whole entry stem-like or affix-like.

## Hermit Crab mapping

Type drives the HC encoding directly: root/stem types become HC **lexical entries** (underlying
lexemes); affix and clitic types become HC **affix processes** keyed to a [[morphosyntactic-analysis]].
A **circumfix** is split into two coordinated affix processes (a prefixal and a suffixal part) that
must co-occur — there is no single circumfix object in HC. Non-concatenative types (simulfix,
suprafix, infix) map to HC morphological rules over the underlying form rather than simple prefixation.

## In our change-sets

Morph type is set when creating an entry or form and is a `morphophonology/*` concern when it controls
attachment:

```yaml
op: lexical.entry.create
lexeme_form: { seh: "-a" }
morph_type: suffix
rationale: "Recurring final -a on verbs is the inflectional final vowel, not part of any root."
confidence: 0.81
```

Changing an entry's morph type (e.g. root → stem) is a high-impact edit: it rewrites how HC attaches
everything downstream.

## QA & parallel relevance

A mis-typed morpheme is a classic silent fault: a suffix entered as a stem will never attach, leaving
words unparsed; a stem entered as a suffix produces spurious over-segmentation. Type checks surface as
"this affix has no host" or "this root never appears alone" flags, and feed
[[interlinearization]] coverage metrics.

## Pitfalls

- **Circumfix ≠ one affix** — it is two coordinated affixes; editing only one half breaks the pair.
- **Clitic vs affix** confusion: a clitic attaches across word boundaries; mistyping it distorts
  morphotactics in [[affix-template-and-slot]]s.
- **Bound root vs stem**: only stems take inflection directly; see [[inflection-vs-derivation]].

## Related & references

[[allomorph]], [[lexical-entry]], [[morphosyntactic-analysis]], [[affix-template-and-slot]],
[[inflection-vs-derivation]]. — FLEx Grammar docs; LibLCM `MasterLCModel.xml` (`MoMorphType`);
Maxwell (2003) on HC affix processes. See [../References.md](../References.md).
