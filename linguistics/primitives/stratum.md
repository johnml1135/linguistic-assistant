# Stratum

> A lexical-phonology rule-ordering layer (Hermit Crab calls these strata): rules apply in order within
> a stratum, strata in sequence. LibLCM *does* model it as `MoStratum`.

**LibLCM class:** `MoStratum`  ·  **FLEx UI:** not surfaced as a stand-alone editor; FieldWorks ships a fixed default set of strata  ·  **Tier:** morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

A stratum is a layer in **lexical-phonology-style** rule organisation. The model partitions the
grammar into ordered levels (classically: a derivational/lexical level, an inflectional level, a
postlexical/word level). [[phonological-rule]]s and affix processes apply **in order within** a
stratum; then the output is handed to the **next** stratum. This captures generalisations like
"derivation feeds inflection, and certain phonological rules only apply after all affixation" — level
ordering that flat rule lists can't express.

## How HC uses it

Hermit Crab is explicitly stratal: its grammar is a sequence of strata, each containing an ordered set
of phonological and morphological rules (SIL.Machine's `Stratum` holds order-preserving rule lists, and
`Language.Strata` is an ordered list composed as a sequential pipeline). HC applies strata **in order to
generate** and runs them **in reverse to analyze** (the same generate-and-test reversal that makes
individual rules bidirectional, Maxwell 1994). Stratum boundaries are therefore real computational
events — a rule placed in the wrong stratum can have its environment fed/bled differently, producing
wrong or missing parses without any error.

## How LibLCM models it

Contrary to a common assumption, LibLCM **does** have a stratum object: **`MoStratum`**, owned in an
ordered sequence on **`MoMorphData.Strata`** (the model comment says the order runs *shallowest to
deepest*). Each `MoStratum` carries `Name`, `Abbreviation`, `Description`, and **`Phonemes`** (a
reference to a `PhPhonemeSet` — its level of representation). Affixes and stems are assigned to a
stratum by reference: **`MoStemMsa.Stratum`** and **`MoDerivAffMsa.Stratum`** (inflectional affixes
inherit their stratum from the affix template they sit in). Phonological rules carry a stratum *span*
via **`PhSegmentRule.InitialStratum`/`FinalStratum`** (unset = applies in all strata). So stratum
membership and ordering *are* recorded in the source `.fwdata`.

The practical wrinkle is on the **FLEx UI** side: FieldWorks ships a fixed default set of strata and
does not expose a general stratum editor, so in everyday FLEx use the stratum structure is largely a
given rather than something the linguist hand-edits. Our change-sets therefore touch stratum
*assignment* far more often than they create strata.

A related loader hazard lives here, and it is real: when the FLEx→HC grammar (the
`SIL.Machine.Morphology.HermitCrab` `XmlLanguageLoader`) wires up the rules of a stratum or the rules of
a template slot, it looks each rule up by id with `TryGetValue` and **no else branch** — so a referenced
rule id that was never registered is **silently dropped**, and parsing proceeds against a quietly
incomplete grammar. (Some other reference kinds — natural classes, primary morphemes — throw instead;
DTD `IDREFS` validation catches only *fully undeclared* ids and only off Mono; and FLEx's own `HCLoader`
deliberately logs-and-skips bad items to emit a partial grammar.) This is exactly the quiet failure the
golden-set gate exists to catch.

## In our change-sets

Stratum ops usually set the stratum *span* of a rule (`PhSegmentRule.InitialStratum`/`FinalStratum`)
or the `Stratum` of a stem/derivational-affix MSA — real source-data references, gated on the golden
set because their effect is invisible to ordinary validation:

```yaml
op: morphophonology.stratum.assign_rule
rule: "spirantization"
initial_stratum: "postlexical"   # -> PhSegmentRule.InitialStratum (MoStratum ref)
final_stratum: "postlexical"     # -> PhSegmentRule.FinalStratum
rationale: "Spirantization must follow devoicing; wrong stratum bled it."
confidence: 0.64
impact: { golden_set_delta: "+5 pass", regressions: 0 }
note: "MoStratum is real .fwdata; FLEx ships a fixed default stratum set, so prefer reassigning to an existing stratum over inventing one."
```

## QA & parallel relevance

Checks: **silently-skipped rule ids** (a referenced rule dropped by the HC loader's `TryGetValue` —
the loader hazard above), **cross-stratum ordering regressions** (caught only by the golden set), and
**stratum-assignment drift** (a rule's `InitialStratum`/`FinalStratum` or an MSA's `Stratum` pointing
somewhere that re-orders feeding/bleeding). Every stratum change is gated on the golden set because its
effects are invisible to ordinary validation.

## Pitfalls

- **`MoStratum` is real `.fwdata`** — strata are editable source data (rule spans, MSA `Stratum`
  refs), not an export-only artefact. But FLEx exposes no general stratum editor and ships a fixed
  default set, so prefer reassigning to an existing stratum over inventing one.
- **Silent rule-id skips** at load time hide missing rules; verify the loaded grammar against the
  intended rule set.
- **Wrong-stratum placement** changes feeding/bleeding with no error — golden set only.

## Related & references

[[phonological-rule]], [[affix-template-and-slot]], [[natural-class]], [[phoneme]]. — Maxwell (2003)
on HC strata, Maxwell (1994) on reverse application; `SIL.Machine` HC implementation (`Stratum`,
`Language.Strata`, `XmlLanguageLoader`); FLEx "Parsing words (Hermit Crab Parser)" doc; Kenstowicz
(1994) on lexical phonology / level ordering; SPE (1968). LibLCM `MasterLCModel.xml` (`MoStratum`,
`MoMorphData.Strata`, `MoStemMsa.Stratum`, `PhSegmentRule.InitialStratum`/`FinalStratum`).
See [../References.md](../References.md).
