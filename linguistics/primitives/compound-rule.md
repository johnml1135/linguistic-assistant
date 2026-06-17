# Compound rule

> A rule that licenses word formation from two (or more) roots — and says which root, if any, is the
> head.

**LibLCM class:** `MoCompoundRule` (abstract) → `MoBinaryCompoundRule` → `MoEndoCompound`, `MoExoCompound`, `MoCoordinateCompound`  ·  **FLEx UI:** "Compound Rule" (Grammar area)  ·  **Tier:** morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

A compound combines two roots into one word. The key typological split is **headedness**:
- **Endocentric** — one member is the **head** and the compound *is a kind of* that head: *blackbird*
  is a bird, *doghouse* is a house. The head supplies category and often inflectional features.
- **Exocentric** — there is no internal head; the compound is *not* a kind of either member:
  *pickpocket* is not a kind of pocket (nor a pick), *redneck* is a person, not a neck.

Headedness governs what category the whole word has and which member's features percolate up.

## How LibLCM models it

`MoCompoundRule` is **abstract**; all concrete rules are owned by `MoMorphData.CompoundRules` (an
ordered sequence — the order is the order in which compounding rules apply in a derivation). The
constituent slots live on the intermediate abstract class **`MoBinaryCompoundRule`**, which owns:
- **`LeftMsa`** and **`RightMsa`** — each an owning atomic `MoStemMsa` ([[morphosyntactic-analysis]])
  stating what each constituent must be (a category, and optionally a feature structure the constituent
  must *have*, not merely unify with).
- **`Linker`** — an optional owning `MoAffixForm` for a semantically empty phoneme string inserted
  between the parts.

The three concrete subclasses add:
- **`MoEndoCompound`** — headed. Adds **`HeadLast`** (a `Boolean`, **defaulting to true**, meaning the
  *right*-hand constituent is the head), and an optional **`OverridingMsa`** (owning atomic `MoStemMsa`)
  whose specified attributes override the corresponding attributes of the head's MSA. Apart from any
  override, the head's category/features percolate to the compound.
- **`MoExoCompound`** — headless. Adds **`ToMsa`** (owning atomic `MoStemMsa`) giving the compound's
  own output category/features, since neither constituent is the head.
- **`MoCoordinateCompound`** — dvandva/appositional, both members are heads; adds no further fields
  (it still inherits the binary `LeftMsa`/`RightMsa` of `MoBinaryCompoundRule`, so the LibLCM model
  is two-constituent even though dvandva compounds can be multi-member cross-linguistically).

*(All four field names corrected/verified against `MasterLCModel.xml`: `LeftMsa`/`RightMsa`/`Linker`
sit on `MoBinaryCompoundRule`; `MoEndoCompound` has `HeadLast` (Boolean, default true) **and**
`OverridingMsa`; the exocentric override field is **`ToMsa`**, NOT `OverridingMsa` — the earlier draft
had this wrong.)*

## Hermit Crab mapping

HC handles compounding as a **morphological rule combining two stems** within a [[stratum]]. The
head's [[morphosyntactic-analysis]] determines the output category and feature inheritance; for
exocentric compounds HC takes the category/features from the output MSA (`ToMsa`) instead, and for
endocentric ones any `OverridingMsa` adjusts the percolated head features. Because compounds multiply
parse possibilities, an over-permissive compound rule (e.g. allowing any noun+noun) is a classic source
of spurious parses in analysis.

## In our change-sets

```yaml
op: morphophonology.compound_rule.create
kind: endocentric            # endocentric | exocentric
left_msa:  { pos: "adjective" }
right_msa: { pos: "noun" }
head: right                  # endocentric only
rationale: "ADJ+N compounds (e.g. 'blackbird' pattern) attested 6× and unparsed."
confidence: 0.66
impact: { unparsed_tokens_affected: 6 }
```

Exocentric ops carry `output_msa:` (→ `MoExoCompound.ToMsa`) instead of `head:`; an endocentric op may
optionally add `overriding_msa:` (→ `MoEndoCompound.OverridingMsa`) to tweak percolated head features.

## QA & parallel relevance

Checks: **over-generation** (a compound rule so broad it admits non-words → spurious parses),
**head/feature mismatch** (an endocentric compound whose declared head can't supply the observed
inflection), and **endo-vs-exo miscoding** (treating a headless compound as headed misroutes feature
percolation). Compare with [[complex-form]], which records *attested* compounds in the lexicon vs the
*generative* rule here.

## Pitfalls

- **Endo vs exo is not stylistic** — it changes category and feature inheritance; get it wrong and
  agreement checks fail downstream.
- **Broad compound rules over-generate** silently in the parser.
- **Lexicalised compounds** ([[complex-form]]) shouldn't be re-derived by a rule and a lexeme both.

## Related & references

[[morph-type]], [[complex-form]], [[morphosyntactic-analysis]]. — FLEx Grammar docs (Compound Rules);
LibLCM `MasterLCModel.xml` (`MoCompoundRule`, `MoBinaryCompoundRule`, `MoEndoCompound`, `MoExoCompound`,
`MoCoordinateCompound`); Maxwell (2003) on HC stem-combining rules; Haspelmath & Sims (2010), Bauer
(2003) on compound headedness. See [../References.md](../References.md).
