# order-the-morphotactics

> Decide the **order** of a word's affixes — assign them to ordered position-class **slots** (an
> [[../primitives/affix-template-and-slot]]) so the grammar stops free-stacking and over-generating.
> Order is *structural* (slot 1 = root-adjacent, slot 2 = next out…), learned from co-occurrence, and
> kept only if it cuts ambiguity without losing coverage.

**Judgment type:** decide (+ verify)  ·  **Grounded in:** position-class / templatic morphology
(Athabaskan, Bantu); affix templates (Maxwell 2003; Lockwood 2011); over-generation / Average Parse
Base (Carroll & Briscoe 1998)  ·  **Used by:** [[../workflows/morphological-parser-setup]],
[[../meta-workflows/steady-state-virtuous-cycle]] (Refactor), [[../meta-workflows/test-a-grammar-theory]]

## The judgment

A grammar can *parse* every form and still be wrong: if affix rules apply in any number and any order,
HC also generates plausible **non-words** (*root-tense-subject* when the language only allows
*subject-tense-root*), and real words get many spurious analyses. That over-generation is an
**ordering** problem, not a coverage problem — and the fix is morphotactic: state the word's
**position classes** as an ordered affix template, each slot optional, **one filler per slot**. This is
the structural complement to [[generalize-not-enumerate]] (which handles a morpheme's *shape*); here we
decide a morpheme's *position*.

The order is **structural, not phonological** — slot 2 always precedes slot 3 whatever fills them — so
do not confuse it with [[../primitives/phonological-rule]] ordering.

## Heuristic / procedure

```
1. Symptom: the data parses (Green) but spurious ambiguity is high / HC emits non-words, or two affixes
   never co-occur in a fixed order under a flat rule list -> suspect free stacking. (assess-grammar's
   ambiguity figure is the trigger.)
2. Learn the order from evidence: for each affix, record its DISTANCE from the root across attested
   words (segment with the known roots + affixes, or read gold IGT morph positions). Root-adjacent =
   slot 1, next out = slot 2, … on each side. (Bantu verb: SUBJ-TENSE-OBJ-root-EXT-FV.)
3. Build the template: one slot per position class, in fixed order, each `Optional`; assign every affix
   to the slot(s) it is attested in (an affix may legitimately fill more than one slot).
4. Emit as an HC affix template (linear morphological-rule order) and VERIFY: keep the ordered template
   ONLY if spurious ambiguity drops AND coverage/recall do not fall ([[read-the-gate]],
   [[assess-grammar]]). Otherwise revert — an over-tight template that blocks valid parses is worse.
```

## Inputs → outputs

- **In:** the induced/known affixes + the corpus (segment to get positions), or gold interlinear morph
  positions; the current (flat/unordered) grammar.
- **Out:** an affix→slot assignment + slot order — a `morphophonology.template.set` op plus per-affix
  slot membership ([[../primitives/morphosyntactic-analysis]] `Slots`) — each carrying rationale,
  confidence, provenance; and a gate verdict (ambiguity dropped, coverage held → accepted).

## Interaction with other skills & the gate

Consumes the affixes [[propose-from-evidence]] surfaced; runs in the **Refactor** step alongside
[[assess-grammar]] (which scores the ambiguity/`DL` improvement) and is bound by [[read-the-gate]] (the
ordered template is accepted only on a clean golden round-trip). Complements
[[generalize-not-enumerate]]: order *and* shape are the two axes of a clean morphology.

## Failure modes / guardrails

- **Two affixes, one slot.** Co-occurring affixes need *distinct* slots; collapsing them blocks the
  word that uses both.
- **Over-tight template.** Forgetting `Optional`, or too few slots, blocks valid parses — gate on
  coverage, not just ambiguity.
- **One slot per affix.** Giving every affix its own slot doesn't reduce ambiguity; group affixes that
  share a genuine position class.
- **Structural vs phonological order.** Template order is fixed regardless of fillers; don't model it as
  a rewrite rule (and vice-versa).
- **Thin evidence.** A position class seen in one or two words is a guess — require enough, or defer.

## From practice (the TDD cycle)

`research/cycle/assign_slots` learns slot ordinals from affix **co-occurrence order**: it greedily
segments frequent words with the induced roots + affixes and records each affix's distance from the
root (it has no gold morpheme breaks, unlike `golden.build_model`). The cycle then emits the ordered
template (`golden.hc` `templated=True`) and keeps it **only if ambiguity drops with coverage held** —
exactly this skill's gate. The motivation was measured: adding prefix induction made the *unordered*
grammar over-generate (ambiguity 12–15) on Swahili/Indonesian/Tagalog; ordered morphotactics is the
principled fix, where the `amb_cap` heuristic was only a band-aid.

**Infixes are a position class too.** Tagalog `-um-`/`-in-` sit *inside* the root (after its onset
consonant: `s-um-ulat`). The cycle induces them (root split = `root[0] + INFIX + root[1:]`) and emits an
HC infix morphological rule (`copy(seg1) + insert + copy(rest)`), placed in an `infix` slot in the
template (prefix → infix → suffix order). Reduplication is the remaining templatic gap.

## Training basis

Position-class / templatic morphology and parser morphotactics (Maxwell 2003; Lockwood 2011); affix
templates in LibLCM (`MoInflAffixTemplate`/`MoInflAffixSlot`, see
[[../primitives/affix-template-and-slot]]); spurious-ambiguity / Average Parse Base (Carroll & Briscoe
1998). See [../References.md](../References.md) §2 (morphology), §6 (finite-state/computational), §11.
