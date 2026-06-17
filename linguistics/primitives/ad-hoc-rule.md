# Ad hoc rule

> A last-resort co-occurrence ban — "these two morphemes (or allomorphs) may not appear together" —
> used when features, classes, and templates can't express the restriction.

**LibLCM class:** `MoAdhocProhib` (abstract) → `MoAlloAdhocProhib`, `MoMorphAdhocProhib`  ·  **FLEx UI:** "Ad hoc rule" (Grammar area)  ·  **Tier:** morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

Sometimes a restriction resists any principled statement: a particular suffix simply never follows a
particular prefix, or one allomorph of a stem is incompatible with one allomorph of an affix, for no
feature-expressible reason. Rather than distort the feature system or [[affix-template-and-slot]]
geometry to encode the quirk, the linguist states it directly as a **prohibition** on co-occurrence.
These are explicitly the *last resort* — every more general mechanism should be tried first, because
ad hoc rules are opaque and don't generalise.

## How LibLCM models it

`MoAdhocProhib` is **abstract** and owns two fields shared by both subclasses: **`Adjacency`** (an
`Integer` enum, below) and **`Disabled`** (a `Boolean` — when true the parser ignores the rule but the
user still sees it). The two subclasses are owned by `MoMorphData.AdhocCoProhibitions`:
- **`MoMorphAdhocProhib`** — bans co-occurrence of **morphemes** (modelled as MSAs). Fields:
  **`FirstMorpheme`** (atomic) plus **`RestOfMorphs`** (a seq), both references to
  `MoMorphSynAnalysis`; it also carries a parallel **`Morphemes`** seq (the full set whose
  co-occurrence is ungrammatical).
- **`MoAlloAdhocProhib`** — bans co-occurrence of specific **allomorphs** (`MoForm`s):
  **`FirstAllomorph`** (atomic) plus **`RestOfAllos`** (a seq — note the name, *not* `RestOfMorphs`),
  and a parallel **`Allomorphs`** seq.

The **`Adjacency`** integer takes five values, verified from the model comment: **Anywhere**,
**SomewhereToLeft**, **SomewhereToRight**, **AdjacentToLeft**, **AdjacentToRight**. (The order of the
`Rest…`/`…morphs` sequence is interpreted left-to-right and only matters when `Adjacency` is not
`Anywhere`.)

*(All field names and the full `Adjacency` enumeration are now verified against `MasterLCModel.xml`;
the earlier "Adjacency values partly unverified" tag is removed. Correction: the allomorph subclass's
remainder field is `RestOfAllos`, not `RestOfMorphs`.)*

## Hermit Crab mapping

HC supports co-occurrence constraints directly — SIL.Machine has `MorphemeCoOccurrenceRule` and
`AllomorphCoOccurrenceRule`, each with a require/exclude `ConstraintType` and a co-occurrence adjacency,
checked during both generation and parsing. A candidate analysis that violates a prohibition is
rejected. They act as filters, not generators: they only ever *remove* otherwise-valid parses, which
makes them effective for blocking over-generation but also makes an over-broad ban a silent cause of
*missing* valid parses.

## In our change-sets

```yaml
op: morphophonology.adhoc_prohib.create
kind: morpheme                 # morpheme | allomorph
first: "PFV-prefix"
rest:  ["HAB-suffix"]
adjacency: anywhere            # anywhere | adjacent_left | adjacent_right | somewhere_left | somewhere_right
rationale: "Perfective + habitual never co-occur; no feature clash captures it."
confidence: 0.6
impact: { spurious_parses_removed: 8, valid_parses_lost: 0 }
```

## QA & parallel relevance

Checks: **over-broad bans** (an ad hoc rule that also blocks attested forms → `valid_parses_lost > 0`
on the golden set), **redundant bans** (the restriction is already enforced by features/templates —
prefer removing the ad hoc rule), and **adjacency mis-set** (anywhere-vs-adjacent errors). The skills
flag any new ad hoc rule for review precisely because it bypasses principled mechanisms.

## Pitfalls

- **Reach for these last.** If a feature, [[inflection-class]], or template can state the
  restriction, do that instead — ad hoc rules are unmaintainable in bulk.
- **Adjacency confusion** changes scope dramatically.
- **Silent over-blocking** removes good parses without erroring; only the golden set catches it.

## Related & references

[[morphosyntactic-analysis]], [[affix-template-and-slot]], [[productivity-restriction]],
[[inflection-class]]. — FLEx Grammar docs (Ad hoc rules); LibLCM `MasterLCModel.xml` (`MoAdhocProhib`,
`MoAlloAdhocProhib`, `MoMorphAdhocProhib`); Maxwell (2003) on HC co-occurrence constraints (SIL.Machine
`MorphemeCoOccurrenceRule`/`AllomorphCoOccurrenceRule`); Lockwood (2011) for a worked example.
See [../References.md](../References.md).
