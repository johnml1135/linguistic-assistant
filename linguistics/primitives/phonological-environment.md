# Phonological environment

> The context — what comes before and after — that conditions whether a rule applies or which
> allomorph is selected.

**LibLCM class:** `PhEnvironment`  ·  **FLEx UI:** "Environment" (e.g. allomorph environments, rule contexts)  ·  **Tier:** morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

A phonological environment states *where* something happens, written in the familiar slash notation
with the focus bar: `/ V _ V` ("between vowels"), `/ _ #` ("word-finally"), `/ # _` ("word-initially").
The underscore marks the position of the affected segment; material to its left is the left context,
to its right the right context; `#` is a word/morpheme boundary. Environments are how
[[allomorph]] selection and [[phonological-rule]] application are made conditional: the *k*→*c*
alternation might be specified as applying only `/ _ [+front, +vowel]`.

## How LibLCM models it

`PhEnvironment` stores the environment as a **`StringRepresentation`** (a `String` — the `/ _ ` notation,
e.g. `/ [C] _ #`; the model calls this the Phase-1 representation that a specialized field editor parses)
**plus** parsed contexts: **`LeftContext`** and **`RightContext`**, each an atomic reference to a
`PhPhonContext` (the regular-expression context tree of sequences, natural-class/segment/boundary simple
contexts, and iteration contexts). It also carries `Name` (`MultiUnicode`) and `Description`
(`MultiString`), and a legacy `AMPLEStringSegment`. *(`StringRepresentation`, `LeftContext`, and
`RightContext` are now verified against `MasterLCModel.xml` — the earlier draft flagged the context-field
names as unverified; that tag is removed.)* Simple contexts reference [[natural-class]]es
(`PhSimpleContextNC`) and [[phoneme]]s (`PhSimpleContextSeg`), and boundary markers (`PhSimpleContextBdry`).
`PhEnvironment`s are owned by the phonology object `PhPhonData` (`Environments`) and *referenced* from:
- `MoAffixAllomorph.PhoneEnv` and `MoStemAllomorph.PhoneEnv` (both reference *collections* of
  `PhEnvironment`) — allomorph conditioning environments. `MoAffixAllomorph` also has a `Position` seq
  of environments for infix placement.
- Phonological-rule contexts (the `LeftContext`/`RightContext` of a `PhSegRuleRHS`, which are themselves
  `PhPhonContext`s rather than full `PhEnvironment` objects).

## Hermit Crab mapping

In HC, environments become the **left and right context** of a phonological rule or the
**required/excluded environment** of an allomorph (in SIL.Machine, an allomorph's
`RequiredEnvironments`/`ExcludedEnvironments`). HC matches
environments during both generation (forward) and parsing (reverse), so an over-broad environment
over-applies a rule in generation *and* admits spurious parses in analysis. Boundary symbols map to
HC's morpheme/word boundary markers; natural-class brackets map to HC natural classes.

## In our change-sets

```yaml
op: morphophonology.environment.set
target: { allomorph: "ka-", entry: "go" }
environment: "/ _ [+vowel]"
rationale: "Prevocalic allomorph 'ka-' was missing its environment; selected everywhere."
confidence: 0.78
impact: { allomorph_selection_changed: 12 }
provenance: { corpus: "mark", refs: ["MRK 1:9"] }
```

## QA & parallel relevance

Checks: **environment overlap** (two allomorphs whose environments both match the same context →
nondeterministic selection), **gaps** (no allomorph covers some context → parse failure),
**unparseable strings** (a class abbreviation that no [[natural-class]] defines), and dangling `#`
placement. These are among the most common silent causes of wrong allomorph choice.

## Pitfalls

- **Overlapping environments** silently make selection order-dependent.
- **Symbol drift** — renaming a natural class breaks every environment string that cited the old name.
- **Boundary confusion** — `_ #` (final) vs `# _` (initial) is an easy and consequential typo.

## Related & references

[[allomorph]], [[phonological-rule]], [[natural-class]], [[phoneme]]. — FLEx Phonology docs ("Build a
phonological rule", environments); LibLCM `MasterLCModel.xml` (`PhEnvironment`, `PhPhonContext`,
`PhSimpleContextNC`/`Seg`/`Bdry`, `MoAffixAllomorph.PhoneEnv`, `MoStemAllomorph.PhoneEnv`); Maxwell
(2003) on HC rule/allomorph environments; SPE (1968), Odden (2013) on rule notation.
See [../References.md](../References.md).
