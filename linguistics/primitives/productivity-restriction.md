# Productivity restriction

> An exception feature that marks *which* stems may undergo a process — the lever that keeps irregular
> forms from being generated like regular ones.

**LibLCM class:** `MoStemMsa.ProdRestrict` / `MoMorphData.ProdRestrict`  ·  **FLEx UI:** "Exception 'Feature'" / "Productivity Restrictions"  ·  **Tier:** morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

Not every morphological process applies to every stem. English regular plural *-s* applies
productively, but *child → children*, *ox → oxen* are exceptions that must *not* also get *-s*
(\**childs*). Conversely some affixes attach only to a marked subclass of stems. A **productivity
restriction** (a.k.a. **exception feature**) is a diacritic on a stem saying "this stem participates
in (or is barred from) this process". It is the standard generative device for blocking
over-generation without inventing a phonological reason that isn't there.

## How LibLCM models it

The vocabulary of restrictions is a **`CmPossibilityList`** held on **`MoMorphData.ProdRestrict`** (an
owning atomic attribute — the project's single list of exception features). Each stem's participation
is recorded on its MSA via **`MoStemMsa.ProdRestrict`** — a *reference collection* of `CmPossibility`
items from that list. Affixes state the restrictions they demand of (or contribute to) the stem on
their own MSAs:
- **`MoInflAffMsa.FromProdRestrict`** — restriction classes the stem must bear for an *inflectional*
  affix to attach (no `To…` form: inflectional affixes cannot add restriction classes).
- **`MoDerivAffMsa.FromProdRestrict`** and **`MoDerivAffMsa.ToProdRestrict`** — a *derivational* affix
  can both require restrictions on its input stem and set the restrictions of the derived output.

*(All verified against `MasterLCModel.xml`: `MoMorphData.ProdRestrict` is a `CmPossibilityList`;
`MoStemMsa.ProdRestrict` is a col of `CmPossibility`; the earlier "whether inflectional affix MSAs
carry their own ProdRestrict" question is **resolved** — they do, via `MoInflAffMsa.FromProdRestrict`,
with derivational affixes additionally carrying `ToProdRestrict`.)* A phonological rule can likewise be
gated on a restriction through a **`PhPhonRuleFeat`** (a rule feature whose `Item` points at the
exception-feature `CmPossibility`), via a RHS's `ReqRuleFeats`/`ExclRuleFeats`.

## Hermit Crab mapping

These map to HC **exception features** (also called MPR — morphologically-conditioned phonological
rule — features / stem diacritics): a feature on a lexeme that a [[phonological-rule]] or affix
process **requires** or **prohibits**. HC checks them during generation (don't apply the process to
an unmarked stem) and parsing (don't accept an analysis that would have required an absent feature).
They are the principled alternative to an [[ad-hoc-rule]] when the restriction is stem-class-based
rather than a one-off pair ban.

## In our change-sets

```yaml
op: morphophonology.prod_restrict.assign
stem: "child"
restrict: ["irregular_plural"]   # must already exist in MoMorphData.ProdRestrict
mode: exclude_from               # exclude_from | require_for
process: "regular_plural"
rationale: "'child' was getting regular -s (*childs); mark it irregular to block."
confidence: 0.82
impact: { overgenerated_forms_blocked: 1, golden_set_delta: "+1 pass" }
```

A separate `prod_restrict.create` op introduces a new restriction possibility before it can be assigned.

## QA & parallel relevance

Checks: **over-generation** (irregular stems still receiving the regular process → the headline use),
**unused restrictions** (a possibility no stem references — possibly dead), and **restriction typos**
(a stem citing a restriction not in `MoMorphData.ProdRestrict`, which can be silently ignored). The
irregular-vs-regular contrast is a recurring data-quality fix the lexeme-building workflows surface.

## Pitfalls

- **Prefer this over [[ad-hoc-rule]]** when the restriction is a stem *class*; reserve ad hoc bans
  for true one-offs.
- **Dangling restriction refs** can be silently dropped — keep the possibility list and assignments
  in sync.
- **Direction confusion** (`require_for` vs `exclude_from`) inverts the whole effect.

## Related & references

[[morphosyntactic-analysis]], [[inflection-class]], [[ad-hoc-rule]], [[phonological-rule]]. — FLEx
Grammar/Parsing docs (exception features, productivity restrictions); LibLCM `MasterLCModel.xml`
(`MoStemMsa.ProdRestrict`, `MoMorphData.ProdRestrict`, `MoInflAffMsa.FromProdRestrict`,
`MoDerivAffMsa.From`/`ToProdRestrict`, `PhPhonRuleFeat`); Maxwell (2003) on HC exception/MPR features;
Bauer (2003), Haspelmath & Sims (2010) on productivity. See [../References.md](../References.md).
