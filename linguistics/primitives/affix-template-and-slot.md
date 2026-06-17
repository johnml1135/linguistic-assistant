# Affix template and slot

> The ordered position-class scaffold for a word: which slots exist, in what order, and which
> inflectional affixes may fill each — the model of templatic/position-class morphology.

**LibLCM class:** `MoInflAffixTemplate` + `MoInflAffixSlot`  ·  **FLEx UI:** "Inflectional Affix
Template" / "Slot"  ·  **Tier:** morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

Many languages build inflected words by filling a fixed sequence of **position classes** (slots), each
holding at most one affix: Bantu verbs run subject–tense–object–root–extension–final-vowel; Athabaskan
verbs have a dozen rigidly ordered prefix slots. A **template** is the whole ordered frame for a
[[part-of-speech]]; a **slot** is one position. Order is structural, not phonological — slot 2 always
precedes slot 3 regardless of what fills them, and a slot may be optional (skipped) or obligatory.

## How LibLCM models it

`MoInflAffixTemplate` is owned by a [[part-of-speech]] (`PartOfSpeech.AffixTemplates`, an owning
sequence). Its ordered slot sequences *(verified)*: `PrefixSlots` and `SuffixSlots` for affixes, plus
`ProcliticSlots` and `EncliticSlots` for clitics — each a reference sequence of `MoInflAffixSlot`. It
also carries `Name`, `Description`, a generic `Slots` reference sequence, `Final` and `Disabled`
(Boolean), `Region` (an `FsFeatStruc` restricting where the template applies, see [[inflection-feature]]),
and `Stratum` (anchoring it to a [[stratum]]).

`MoInflAffixSlot` fields: `Name`, `Description`, and `Optional` (Boolean) *(verified)*. A slot is
filled by the `MoInflAffMsa`s that list it in their `Slots` reference — i.e. an inflectional affix
declares which slot(s) it occupies (see [[morphosyntactic-analysis]]). One filler per slot per word.

## Hermit Crab mapping

Templates and slots are HC's **morphotactics**: the template's ordered slots become the order in which
HC affix processes may apply, and `Optional` controls whether the slot must be filled. This is what
keeps HC from generating *root-tense-subject* when the grammar says *subject-tense-root*. Templates are
typically anchored to a [[stratum]], so derivation (stem-building) finishes before the inflectional
template applies — mirroring [[inflection-vs-derivation]].

## In our change-sets

Template/slot edits are `morphophonology/*` structural ops:

```yaml
op: morphophonology.template.set
part_of_speech: verb
prefix_slots: [subject, tense]      # ordered
suffix_slots: [final-vowel]
rationale: "Verbs show fixed SUBJ-TENSE-root-FV order across the corpus; encode as one template."
confidence: 0.74
```

Assigning an affix to a slot is a separate op linking its `MoInflAffMsa.Slots`.

## QA & parallel relevance

Slot-order errors are a leading cause of silent over-generation: a misordered template lets HC produce
plausible non-words, which the golden-set regression gate is designed to catch (see
[[interlinearization]]). In parallel-QA, a target word that needs two affixes competing for one slot
signals either a template gap or a wrong slot assignment.

## Pitfalls

- **Two affixes, one slot** — only one filler is allowed; co-occurring affixes need distinct slots.
- **Confusing template order (structural) with rule order (phonological)** — see [[phonological-rule]].
- **Forgetting `Optional`** makes a skippable slot obligatory, blocking valid parses.

## Related & references

[[morphosyntactic-analysis]], [[inflection-class]], [[inflection-feature]], [[stratum]],
[[morph-type]], [[inflection-vs-derivation]]. — FLEx Grammar docs; LibLCM `MasterLCModel.xml`
(`MoInflAffixTemplate`, `MoInflAffixSlot`); Lockwood (2011); Maxwell (2003). See
[../References.md](../References.md).
