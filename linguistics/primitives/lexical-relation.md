# Lexical relation

> A typed link between entries or senses — synonym, antonym, part/whole, etc. — stored as a relation
> instance of a defined relation type.

**LibLCM class:** `LexReference` (instance) + `LexRefType` (type)  ·  **FLEx UI:** "Lexical Relations" (on entries/senses)  ·  **Tier:** lexical  ·  **In MiniLcm:** partial

## What it is (linguistics)

Words and meanings relate to one another: **synonymy** (*big ~ large*), **antonymy** (*hot ~ cold*),
**hyponymy / part-whole** (*finger* is part of *hand*; *rose* is a kind of *flower*), and ordered
**scales/sequences** (*Monday → Sunday*; *cold → cool → warm → hot*). Capturing these turns a lexicon
into a semantic network and supports thesaurus generation, sense disambiguation, and consistency
checks. The two halves are the **relation type** (what kind of link, and how it reads in each
direction) and the **relation instance** (the actual set of related items).

## How LibLCM models it

- **`LexRefType`** (a `CmPossibility`) **defines** a relation type. Key fields: **`MappingType`** (an
  Integer-as-enum), **`ReverseName`** / **`ReverseAbbreviation`** (the label seen from the *other* end
  — e.g. "whole" vs "part"), and **`Members`** (an owning collection of the actual `LexReference`s of
  this type). Types live in the `LexDb.References` possibility list.
- **`MappingType`** is a `basic` Integer (`min="0" max="127"`) used as an enum; the defined values
  `0–8` encode target class **and** structure: `0` sense collection, `1` sense pair, `2` sense tree,
  `3` sense sequence, `4` entry collection, `5` entry pair, `6` entry tree, `7` entry-or-sense
  collection, `8` entry-or-sense tree (one to ordered many). "Collection" = unordered many-many
  (synonyms); "pair" = one-to-one (antonym); "tree" = one-to-many asymmetric (part/whole, uses
  ReverseName); "sequence/scale" = ordered.
- **`LexReference`** is one **instance**: **`Targets`** (a reference **sequence** of `CmObject` — the
  related entries and/or senses), plus `Name` and `Comment`. Order in `Targets` matters for tree
  (first = the whole/generic) and sequence types.

## Hermit Crab mapping

None. Lexical relations are semantic/lexicographic links; Hermit Crab ignores them. They serve the AI
skills and QA layers, not the morphological parser.

## In our change-sets

Creating a relation is a `lexical/*` op:

```yaml
op: lexical.relation.create
type: "Antonym"          # LexRefType, MappingType=1 (sense pair)
targets: ["kupisa#1", "kutonhora#1"]   # hot / cold senses
rationale: "Corpus contrast pair; aids sense disambiguation."
confidence: 0.7
```

For tree types the first target is the whole/generic (ReverseName end). Ops carry
rationale/confidence/impact/provenance.

## QA & parallel relevance

Relations power **consistency checks**: if A is marked synonym of B, do their glosses/domains agree?
Antonym pairs and part-whole trees help validate [[sense]] divisions and surface gaps. In
[[parallel-translation-qa]], synonym sets help recognize that a source term may legitimately be
rendered by any member of a synonym set in the target.

## Pitfalls

- **Pick the right `MappingType`** — a symmetric synonym set (collection) vs a directional part-whole
  (tree) read very differently; the wrong type breaks the reverse label.
- **Target-order significance** — for tree/sequence types `Targets` order is meaningful (first = whole
  / start); for collections it is not.
- **Mixing entry- and sense-level targets** is only valid for MappingType 7/8.
- **Relation vs domain**: a [[semantic-domain]] groups by topic; a lexical relation is a specific typed
  link — don't substitute one for the other.

## Related & references

[[sense]], [[lexical-entry]], [[semantic-domain]], [[homograph-number]]. — FLEx Lexicon docs; LibLCM
`MasterLCModel.xml` (`LexRefType` with `MappingType` Integer 0–127, enum values 0–8;
`LexReference.Targets`); Atkins &
Rundell (2008) on sense relations; GOLD ontology on relation types. See [../References.md](../References.md).
