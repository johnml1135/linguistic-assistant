# Phonological rule

> An ordered SPE-style rewrite that maps underlying forms to surface forms — applied forward to
> generate and in reverse to parse.

**LibLCM class:** `PhSegmentRule` → `PhRegularRule`, `PhMetathesisRule`  ·  **FLEx UI:** "Phonological Rule" (Grammar area)  ·  **Tier:** morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

A phonological rule expresses a sound alternation as a rewrite: **A → B / C _ D** ("A becomes B
between C and D"). Intervocalic voicing, final devoicing, spirantization, and vowel harmony are all
written this way. Rules are **ordered**: an earlier rule can create or destroy the environment a later
rule needs (feeding/bleeding), so the same set of rules in a different order produces different
surface forms. This ordering is the heart of classical generative phonology — and the main hazard for
a parser.

## How LibLCM models it

The abstract base is **`PhSegmentRule`** (carrying `Name`, `Description`, a `Direction` integer —
0 left-to-right iterative, 1 right-to-left iterative, 2 simultaneous — a `Disabled` flag, the structural
description, and the [[stratum]] span). Its rules are owned in an **ordered** sequence on the phonology
object `PhPhonData` (`PhonRules`). Two concrete subclasses:
- **`PhRegularRule`** — an SPE rewrite. **`StrucDesc`** (on `PhSegmentRule`; an owning seq of
  `PhSimpleContext`) gives the structural description (the *A* to match — if empty, the rule is
  epenthetic). **`RightHandSides`** is an owning sequence of **`PhSegRuleRHS`**, each carrying the
  structural change (`StrucChange`, a seq of `PhSimpleContext` — empty means a deletion) plus its
  **`LeftContext`/`RightContext`** ([[phonological-environment]] contexts). A RHS may also restrict by
  `InputPOSes` and by required/excluded rule features (`ReqRuleFeats`/`ExclRuleFeats`,
  see [[productivity-restriction]]). Multiple RHSs let one rule have several context-specific outputs.
- **`PhMetathesisRule`** — reordering of segments (no segment is added or deleted), e.g. CV→VC. Its
  `StrucChange` is a `String` holding an ordered, space-separated list of integers, each indexing a
  position in the shared `StrucDesc` — so it encodes which positions swap rather than a substitution.

*(All field names above — `StrucDesc`, `RightHandSides`, `PhSegRuleRHS`, its `LeftContext`/`RightContext`/
`StrucChange`, `Direction`, and the metathesis `StrucChange` integer-string — are now verified against
`MasterLCModel.xml`; the earlier draft's "metathesis sub-field names partly unverified" tag is removed.)*

A rule can also be scoped to a stratum span via **`InitialStratum`/`FinalStratum`** (references to
`MoStratum`); if unset, the rule applies in all strata. Rules reference [[natural-class]]es and
[[phoneme]]s through their simple contexts; their position in the ordered list is load-bearing.

## Hermit Crab mapping

HC's phonology *is* ordered SPE rewrites, so `PhRegularRule`s map almost directly to HC phonological
rules within a [[stratum]]. The crucial property, confirmed in both Maxwell (1994) and the SIL.Machine
source: HC applies rules **forward to generate** and runs the ordered list **in reverse to analyze** —
the generate-and-test algorithm "unapplies" each rule from surface back toward the underlying form
(SIL.Machine's `AnalysisStratumRule` literally `.Reverse()`s the rule order; the synthesis path applies
them forward). Reversibility means rule **order** matters twice over — a mis-ordered rule can produce a
form that *looks* fine in generation yet causes the reverse pass to silently mis-parse or skip a valid
analysis. This is exactly why the **golden-set test gate** is mandatory: ordering bugs do not announce
themselves.

## In our change-sets

```yaml
op: morphophonology.rule.create
kind: regular
struc_desc: "[+stop, -voice]"
change: "[+continuant]"
environment: "/ [+vowel] _ [+vowel]"
order_after: "nasal_assimilation"
rationale: "Intervocalic spirantization unrules 'aba'→'apa' overgeneration."
confidence: 0.7
impact: { golden_set_delta: "+9 pass", regressions: 0 }
```

Every rule op must declare its **ordering** (`order_after`/`order_before`) and is gated on the golden
set before acceptance.

## QA & parallel relevance

Checks: **ordering regressions** (the golden-set diff is the gate), **rules that never fire** (dead
rules — possible mis-ordering or wrong environment), **over-application** (a rule whose class/env is
too broad), and **non-reversible** outputs that break round-trip parse. Mis-ordering is the canonical
silent-wrong-parse failure mode in this whole subsystem.

## Pitfalls

- **Order is silent.** Wrong order rarely errors; it just yields wrong parses — catch it with the
  golden set, never by eyeballing.
- **Feeding/bleeding surprises** when a rule is inserted mid-list.
- **Generation-only validation** misses reverse-parse breakage; always test both directions.

## Related & references

[[stratum]], [[natural-class]], [[phonological-environment]], [[phoneme]],
[[productivity-restriction]]. — FLEx Phonology docs ("Build a phonological rule"); LibLCM
`MasterLCModel.xml` (`PhSegmentRule`, `PhRegularRule`, `PhSegRuleRHS`, `PhMetathesisRule`,
`PhPhonRuleFeat`); Maxwell (1994) reverse-ordered rules (and SIL.Machine's `AnalysisStratumRule`),
Maxwell (2003); SPE (1968), Kenstowicz (1994). See [../References.md](../References.md).
