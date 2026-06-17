# generalize-not-enumerate

> When a morpheme shows several surface shapes, prefer stating **one phonological rule over a natural
> class** to listing the allomorphs — but only if the rule survives the golden-set round-trip.

**Judgment type:** decide (+ propose)  ·  **Grounded in:** SPE evaluation metric (Chomsky & Halle
1968); Martinet (1955) economy; Zwicky (1985); Nida (1949)  ·  **Used by:**
[[../workflows/morphological-parser-setup]], [[../workflows/interlinearization]],
[[../meta-workflows/steady-state-virtuous-cycle]], [[../meta-workflows/close-the-zero-parse-loop]],
[[../meta-workflows/test-a-grammar-theory]], [[../meta-workflows/bootstrap-a-new-language]]

## The judgment

This is the skill that turns the model from a *describer* into an *analyst*. Left alone, an LLM (like
a first-year field-methods student) will faithfully **enumerate** what it sees — listing
`-s / -z / -əz` as three [[../primitives/allomorph]]s of the plural. A trained linguist instead asks
*"is there one generalization here?"* and writes a single [[../primitives/phonological-rule]] over a
[[../primitives/natural-class]]. Capturing the generalization is the **evaluation metric** of
generative phonology: of two analyses that fit the data, the one with fewer, more general statements
is better (SPE; Martinet's *économie*).

This is the practitioner observation that motivated the whole skill layer: *the model produced words
and rules out of the box, but had to be taught to generalize (phonological rules instead of
allomorphy) to get rolling.*

## Heuristic / procedure

When ≥2 allomorphs of one morpheme are on the table:

```
1. Are the alternants predictable from PHONOLOGICAL context?
   ├─ YES → do the shapes' environments form a NATURAL CLASS?
   │        ├─ YES → propose ONE phonological rule over that class; drop the listed allomorphs
   │        └─ NO  → keep allomorphs, but flag "environment not natural — look for a missing class"
   ├─ predictable from MORPHOLOGICAL context (class/feature, not sound)?
   │        → keep as listed allomorph(s) with the conditioning feature (Zwicky: morphologically conditioned)
   └─ NO pattern (arbitrary)?
            → suppletion: separate forms / entries (do NOT invent a rule)
```

Then **always verify, never assume**: a plausible rule can be plausibly *wrong* (mis-ordered rules
parse silently wrong). Generate the expected surface forms with Hermit Crab, run the golden
`word→gloss` set, and keep the rule **only if** failures drop *and no regressions appear*
([[read-the-gate]]). Prefer the rule; respect the gate.

## Inputs → outputs

- **In:** a morpheme with multiple attested surface forms + their environments (from
  [[../workflows/interlinearization]] or a zero-parse cluster); the phoneme/[[../primitives/natural-class]]
  inventory.
- **Out:** either a `morphophonology/*` op adding a [[../primitives/phonological-rule]] (and removing
  now-redundant allomorphs), or a justified decision to keep allomorphs / treat as suppletion — each
  with rationale, confidence, and provenance.

## Interaction with other skills & the gate

Feeds on [[propose-from-evidence]] (which surfaces the alternation) and is bounded by
[[read-the-gate]] (which accepts/rejects the generalization). Over-generalization is the failure mode,
so the gate is non-negotiable here. When the rule needs a class that doesn't exist yet, it proposes
the [[../primitives/natural-class]] too.

## Failure modes / guardrails

- **Over-generalization** — positing a rule that also rewrites forms it shouldn't. Caught by golden-set
  regressions; if it can't pass without exceptions, prefer allomorphs + a
  [[../primitives/productivity-restriction]] over a leaky rule.
- **Rule ordering** — an ordered rule can feed/bleed others; HC applies rules in reverse to analyze, so
  test **both** parse and generate ([[../primitives/stratum]]).
- **Forcing a rule onto suppletion** — arbitrary alternation (be/was) is not a rule; don't manufacture
  one.
- **Premature generalization** from one or two examples — require enough evidence, or
  [[guess-ask-or-defer]] to a speaker.

## Training basis

SPE (Chomsky & Halle 1968) and Martinet (1955) on the evaluation metric / economy; Zwicky (1985) on
the rule/allomorph/suppletion decision; Nida (1949) on identifying conditioning; Kenstowicz (1994) on
rule writing. See [../References.md](../References.md) §2–3, §9.
