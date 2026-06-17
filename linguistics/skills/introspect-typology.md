# introspect-typology

> Before (and while) analyzing a language, **predict its likely — and especially its *marked/surprising*
> — features** from family/areal priors, so the loop knows what to look for first.

**Judgment type:** predict  ·  **Grounded in:** Pike (1947) monolingual demonstration; WALS / Grambank
/ PHOIBLE; "interesting features first" (LAMP, Brewster & Brewster 1976)  ·  **Used by:**
[[../meta-workflows/bootstrap-a-new-language]], [[../workflows/morphological-parser-setup]]

## The judgment

A trained field linguist does not approach a new language as a blank slate. From the genus, family,
and area they already *expect* a profile — agglutinating or fusional, SOV or SVO, case-marking or not,
a five-vowel system or a tonal one — and they let that expectation steer elicitation. This skill builds
that prior **fast** (Pike's monolingual demonstration is the human analogue: construct a working model
from zero in hours), then ranks what to investigate by **information value**: the *marked or surprising*
features — ejectives, noun classes, switch-reference, ergativity — are worth chasing first because
confirming or refuting them most reshapes the model.

## Heuristic / procedure

```
1. Identify the language (Ethnologue) → genus, family, macro-area, neighbours.
2. Pull typological priors:
   ├─ WALS      → morphology type, basic word order, case, agreement, alignment
   ├─ Grambank  → binary morphosyntax features (has-X? present/absent)
   └─ PHOIBLE   → phoneme-inventory norms for the family/area
3. Form a profile, then RANK what to look for by markedness:
   ├─ feature is areally/typologically COMMON → low priority (assume, verify cheaply later)
   └─ feature is MARKED / surprising for this profile → HIGH priority (chase first)
4. Emit a "what to look for" prior: a ranked hypothesis list, each tagged with its source + confidence.
```

The rank-by-markedness step is the point: a feature the priors say is *unlikely here but possible* has
the highest expected information; spending early elicitation there pays off most.

## Inputs → outputs

- **In:** a language identification (ISO code / family), plus any seed wordlist or text.
- **Out:** a ranked **prior** — expected morphology type, word order, case/agreement, phoneme-inventory
  expectations, and a flagged list of *interesting features to confirm first* — feeding
  [[../meta-workflows/bootstrap-a-new-language]] and the initial [[../workflows/morphological-parser-setup]].
  Each item carries source (WALS/Grambank/PHOIBLE) and confidence; none are committed as fact.

## Interaction with other skills & the gate

This skill runs *upstream* of the loop: it seeds what [[propose-from-evidence]] should look for and
what [[prioritize-the-backlog]] should weight early. It writes no [[../primitives/lexical-entry]] or
[[../primitives/phonological-rule]] directly — every prior must still earn its place at
[[read-the-gate]] via the language's own data. It can sharpen [[generalize-not-enumerate]] by
suggesting which [[../primitives/natural-class]]es to expect.

## Failure modes / guardrails

- **Priors are hypotheses, not facts.** Confirm against the language's own data; a related language is
  evidence, not authority.
- **Don't impose a template.** The single biggest risk is forcing the language into the family's mold
  (the "WALS says so, therefore it is" trap) — every marked-feature prediction must be falsifiable and
  flagged for confirmation.
- **Sparse coverage.** WALS/Grambank rows for small languages are often blank or based on one source;
  treat single-source values as weak *(unverified)*.
- **Over-chasing the exotic.** Markedness sets *priority*, not *certainty* — don't manufacture an
  ejective series because the area has them.

## Training basis

Pike (1947) on building a phonemic/working model fast (the monolingual demonstration); WALS, Grambank,
and PHOIBLE as typological priors; Brewster & Brewster (LAMP, 1976) and Whaley (1997) on
"interesting features first." See [../References.md](../References.md) §8, §9, §10.
