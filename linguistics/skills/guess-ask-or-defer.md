# guess-ask-or-defer

> Route every uncertain decision to exactly one of three actions — **guess** (propose now), **ask a
> native speaker** (present 2–3 concrete options), or **defer** (leave a backlog flag) — by weighing
> confidence against the cost of being wrong and against *who* can actually answer.

**Judgment type:** decide  ·  **Grounded in:** field elicitation practice (Bowern 2015; Vaux & Cooper
1999); the project's accessibility goal  ·  **Used by:** *all* workflows
([[../workflows/interlinearization]], [[../workflows/sense-discovery-and-disambiguation]],
[[../workflows/parallel-translation-qa]], …); meta-workflows
[[../meta-workflows/steady-state-virtuous-cycle]] and [[../meta-workflows/build-the-lexicon]]

## The judgment

This is the heart of the accessibility differentiator. A fixed parser has exactly one response to
uncertainty: fail silently or guess blindly. A trained linguist instead *routes* the uncertainty —
some calls they make themselves, some they take to a speaker, some they honestly shelve. The skill
encodes that triage so an **untrained native speaker** becomes a first-class contributor: the model
does the linguistics, the speaker supplies the one thing only they have — *acceptability and meaning
judgments in their own language*. The output side of "ask" is always phrased by
[[phrase-for-a-speaker]].

The three actions are not a confidence slider alone. They turn on three axes: **confidence** (how
strong is the evidence?), **reversibility / impact** (what does a wrong guess cost downstream — a
silently mis-parsed corpus, a bad lexicon entry?), and **answerability** (can a *speaker* settle this,
or does it need a trained linguist?). A speaker can say *which sounds right*; only a linguist can
decide *whether this is a stratum-2 rule*.

## Heuristic / procedure

```
For each uncertain decision:
1. Is confidence HIGH and evidence convergent?
   ├─ YES → and impact-of-error LOW/reversible?  → GUESS (propose now, mark confidence)
   └─ YES → but impact HIGH/irreversible?         → ASK (confirm before committing)
2. Confidence MEDIUM/LOW?
   ├─ Can a NATIVE SPEAKER resolve it (meaning / acceptability / minimal pair)?
   │        → ASK — hand to [[phrase-for-a-speaker]] with 2–3 concrete options
   ├─ Needs a TRAINED LINGUIST (analysis, theory, stratum)?
   │        → DEFER to the linguist backlog (do NOT ask the speaker)
   └─ Insufficient evidence for anyone yet?
            → DEFER: leave a backlog flag (datum + what would resolve it), move on
```

Confidence and impact are recorded on every proposal so [[prioritize-the-backlog]] can re-rank
deferred items as evidence accumulates.

## Inputs → outputs

- **In:** an uncertain decision from any workflow — a candidate sense, allomorph, gloss, rule, or QA
  flag — with its evidence and a confidence estimate.
- **Out:** one routed action: a **proposal** (guess, with confidence + provenance), a **speaker
  question** (handed to [[phrase-for-a-speaker]]), or a **backlog flag** (defer, with the datum and the
  evidence that would unblock it). Deferring is a valid, honest outcome — not a failure.

## Interaction with other skills & the gate

Every change skill funnels through here: [[propose-from-evidence]] and [[generalize-not-enumerate]]
emit candidates that this skill routes. "Guess" outcomes still face [[read-the-gate]] before commit —
routing to *propose* is not the same as accepting. "Ask" outcomes are realized by
[[phrase-for-a-speaker]]; "defer" outcomes flow to [[prioritize-the-backlog]].

## Failure modes / guardrails

- **Guessing on high-impact, low-confidence items** — the cardinal error; a confident-sounding wrong
  guess corrupts the data silently. Impact overrides confidence: when wrong is expensive, ask or defer.
- **Asking a speaker a linguist's question** — speakers judge meaning and acceptability, not theory; a
  question only a linguist can answer must be deferred, not delegated to the speaker.
- **Treating defer as failure** — shelving with a clear flag is the honest move; never manufacture a
  guess to avoid a blank.
- **Routing without recording confidence/impact** — undermines later re-ranking by
  [[prioritize-the-backlog]].

## Training basis

The triage mirrors standard field-methods practice: elicit what speakers can judge, reserve analysis
for the linguist, and log the rest (Bowern 2015; Vaux & Cooper 1999; Payne 1997). The accessibility
goal — an untrained speaker as contributor — is the project's own design premise. See
[../References.md](../References.md) §4, §9.
