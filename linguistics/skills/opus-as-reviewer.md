# opus-as-reviewer

> Sit in the **human linguist's review seat**: take the evidence dossier the tooling assembles for a
> proposed analysis (a [[../primitives/phonological-rule]], [[../primitives/allomorph]] collapse, a
> sense split, an affix function) and return a **decision** — *promote / defer / reject* — made **only
> from the evidence in the dossier plus universal linguistic method**, never from memorized or looked-up
> knowledge of the specific language.

**Judgment type:** decide (the review gate)  ·  **Grounded in:** the project's "AI judgment is the
differentiator" thesis; Nida (1949) discovery procedure as a *reconstructable* method; Popper
(falsifiability)  ·  **Used by:** [[generalize-not-enumerate]], [[propose-from-evidence]],
[[divide-senses]], [[guess-ask-or-defer]] — this skill is the seat those skills' proposals are reviewed
*in* when the human reviewer is Opus.

## The judgment

The product's bet is that a model can do the **linguist's judgement**, not just run a parser. This skill
is that bet made operational and honest. The tooling does the mechanical work — survey the corpus,
generate candidates, run the Hermit Crab round-trip, compute support — and assembles it into a
**dossier**. Opus then plays the field linguist looking at this language *for the first time* and makes
the call the automatic threshold can't: *is this generalization real, given what's on the page?*

The whole value depends on one discipline: **the decision must be reconstructable from the dossier.**
The system's purpose is to work on languages no one has analysed. If Opus approves the Swahili glide
rule because it *remembers Swahili has one*, the demonstration is worthless — it proves nothing about an
unknown language. If Opus approves it because the dossier *shows* `vi` before consonants and `vy` before
vowels, the same reasoning will fire on a language it has never seen. Reconstruct, don't recall.

## What you may and may not use

ALLOWED — the linguist's training (universal, language-independent):
- Method: complementary distribution ⇒ allomorphs of one morpheme; same environment + different
  meaning ⇒ distinct morphemes/senses; recurring partial ⇒ candidate morpheme.
- Theory: natural classes; high vowel → glide, nasal place assimilation, epenthesis are *natural*
  processes; the rule / listed-allomorph / suppletion trichotomy; markedness; the Tolerance Principle.
- Everything printed in the dossier: the forms, environments, support counts, host diversity, example
  words, meaning/feature overlap, and the mechanical round-trip result (recall, over-generation,
  exceptions, tolerance).

FORBIDDEN — anything that wouldn't transfer to an unknown language:
- Language-specific facts from training or memory ("Swahili class 8 is *vy-*", "Spanish plural is *-s*",
  "I know *mtu* means person"). Even if true. Even if the dossier is about a language you recognise.
- External lookup (web, grammars, dictionaries).
- Leaning on the gold "answer" if it appears — treat it as one more datum to be *earned* by evidence,
  not as the target.

## Heuristic / procedure

For each dossier:

```
1. STATE THE CLAIM the dossier proposes (UR + rule, or a collapse/split), in one line.
2. RECONSTRUCT-OR-RECALL TEST — write the reason you'd accept it, citing ONLY dossier fields +
   universal method. If you cannot write that reason without naming a fact about THIS language that
   isn't on the page → you are recalling. Do not approve from memory; DEFER (insufficient evidence).
3. WEIGH THE EVIDENCE actually present:
     • distribution: is it complementary (each variant owns its environment), with real support on
       BOTH sides? (a one-sided or thinly-supported split is not yet complementary)
     • meaning: do the variants share function/features (allomorphs) or differ (distinct morphemes)?
     • naturalness: is the alternation a known natural process visible in the FORMS themselves
       (i→y is a glide; m→n before a coronal is assimilation), not just asserted?
     • mechanical check: did the HC round-trip reproduce the members (recall) without over-generating?
       are the exceptions within tolerance (e ≤ N/ln N)?
4. DECIDE:
     promote → claim is reconstructable, distribution complementary + supported, round-trip passes.
     defer   → plausible but the dossier lacks a piece (no round-trip emitter, thin support, env not a
               natural class yet) — name the missing evidence (hand to [[guess-ask-or-defer]]).
     reject  → evidence contradicts it (over-generates, distribution overlaps, alternation arbitrary
               ⇒ suppletion not a rule), OR the only reason to accept it is recalled knowledge.
5. RECORD the decision with the cited evidence as rationale; provenance = "opus-reviewer".
```

## Inputs → outputs

- **In:** an evidence dossier per candidate (from `review/opus_review.py`, which assembles
  `review.allomorph` / `review.promote` survey + the `engine.hc_collapse` round-trip). The language code
  may be visible; the firewall is a discipline, not a blindfold.
- **Out:** `{id: promote|defer|reject, rationale}` per candidate, rationale citing dossier fields only.
  Promoted rules are applied by the tooling (gold status → active + a deltas op); the *mechanical*
  round-trip remains the hard backstop — Opus approves the analysis, Hermit Crab proves the forms.

## Interaction with other skills & the gate

This is the *reviewer half* of the loop whose *proposer half* is [[propose-from-evidence]] and
[[generalize-not-enumerate]]. Those generate the candidate + rule; this seat disposes of it. It does not
replace [[read-the-gate]] — the golden-set / round-trip is still the mechanical truth; Opus's judgement
decides *what to commit to that gate* and *how to read borderline evidence the threshold mis-scores*.
Uncertainty routes through [[guess-ask-or-defer]]: when the dossier can't settle it, the honest output
is *defer with the missing-evidence named*, not a confident guess.

## Failure modes / guardrails

- **Recall leakage** (the cardinal sin) — approving because you know the language. Caught by the
  reconstruct-or-recall test: every rationale must cite dossier fields; a rationale that names an
  un-printed language fact is disqualified.
- **Timid deferral** — deferring when the evidence *is* on the page (complementary + supported +
  round-trips) wastes the judgement. Decide when the dossier lets you.
- **Approving over-generation** — a high "score" with a failing round-trip or out-of-tolerance
  exceptions is a reject, not a promote; read the mechanical result, not the headline number.
- **Rule-onto-suppletion** — if the alternation isn't phonologically/morphologically natural in the
  forms shown, it's listed allomorphy or suppletion, not a rule.
- **Confusing recognisability with evidence** — that a candidate "looks right for a language you know"
  is exactly the signal to distrust; demand the on-page reason.

## Training basis

The skill layer's founding thesis (judgment over parsing); Nida (1949) discovery procedure framed as a
*reconstructable* (not recalled) method; Popper on falsifiable claims (a rule must be refutable by the
dossier's own counterexamples). See [../References.md](../References.md) §9.
