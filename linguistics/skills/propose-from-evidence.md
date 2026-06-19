# propose-from-evidence

> From a single datum — an unparsed wordform, a paradigm, a parallel pair — **propose a concrete
> analysis** (a [[../primitives/lexical-entry]], [[../primitives/sense]], [[../primitives/allomorph]],
> or [[../primitives/phonological-rule]]) with rationale, confidence, and provenance.

**Judgment type:** propose  ·  **Grounded in:** Nida (1949) discovery procedure; Payne (1997)  ·
**Used by:** most change workflows — [[../workflows/interlinearization]],
[[../workflows/morphological-parser-setup]], [[../workflows/sense-discovery-and-disambiguation]],
[[../workflows/parallel-translation-qa]]

## The judgment

This is the **front of the loop**. Given data the parser couldn't handle — a zero-parse wordform, a
gap in a paradigm, a translation pair that doesn't line up — the skill turns observation into a
*specific, committable proposal*. It is the inverse of generalization: where
[[generalize-not-enumerate]] *collapses*, this skill *generates the candidate* that collapsing later
operates on. The trained move is Nida's discovery procedure: don't guess a morpheme from one token,
**find the recurring partial** across forms, then prove it behaves like a morpheme.

## Heuristic / procedure

Nida's discovery procedure, made operational:

```
1. RECURRING PARTIALS — does a form/meaning chunk recur across ≥2 data points?
      no  → not yet a morpheme; flag for more data ([[guess-ask-or-defer]])
      yes ↓
2. SEGMENT — isolate the recurring partial vs the residue.
3. COMPLEMENTARY DISTRIBUTION — do candidate variants occur in mutually exclusive environments?
      yes → same morpheme, multiple [[../primitives/allomorph]]s
      no  → distinct morphemes (or distinct [[../primitives/sense]]s — hand to [[divide-senses]])
4. PHONOLOGICAL CONDITIONING — is the variation predictable from sound?
      yes → propose [[../primitives/phonological-rule]] (then [[generalize-not-enumerate]])
      no  → propose listed allomorph / lexical entry
5. PROPOSE with rationale + confidence + provenance (which data points motivated it).
```

## Inputs → outputs

- **In:** a datum — unparsed wordform, paradigm slice, or aligned parallel pair — plus the current
  lexicon/grammar state.
- **Out:** a concrete proposal (new [[../primitives/lexical-entry]], [[../primitives/sense]],
  [[../primitives/allomorph]], or [[../primitives/phonological-rule]]) as a change-set op, each tagged
  rationale / confidence / provenance. Never a silent commit.

## Interaction with other skills & the gate

It opens the loop and hands off: alternations go to [[generalize-not-enumerate]] (collapse to a rule);
meaning splits go to [[divide-senses]]; low-confidence cases route through [[guess-ask-or-defer]]
(possibly [[phrase-for-a-speaker]]). Every proposal it makes is **gated by [[read-the-gate]]** — it
proposes, the golden set disposes.

## Failure modes / guardrails

- **One example is a hypothesis, not a morpheme.** A single token never licenses a commit; require
  recurrence or [[guess-ask-or-defer]].
- **Spurious partials.** Accidental form overlap (English *-er* in *butter*) is not a morpheme — demand
  a consistent meaning correlate, not just shared letters.
- **Mistaking a sense split for an allomorph split** (or vice versa) — route distribution failures to
  [[divide-senses]].
- **Provenance drift.** A proposal without its motivating data points can't be re-evaluated when the
  corpus grows; always attach provenance.

## From practice (morpheme analysis → reusable scenarios)

`research/cycle/llm_propose.py` operationalizes this skill on the cycle's hardest residue: *what is this
affix?* It curates the evidence (the affix's side, slot, attaching POS, the English its morpheme aligned
to via `morph_align.py`, and real examples) and asks a model for a structured analysis (label, category,
gloss, confidence, rationale). Two reusable properties matter: the model is **swappable by config** (Opus
4.8 now; Qwen 3.6 / Gemma 4 later, same prompt + schema via the `harness/` endpoints; a deterministic
heuristic is the offline baseline), and **every call is banked as a self-contained scenario** (evidence
→ question → answer in `out/<pair>_scenarios.jsonl`). The curation — the hard linguistic context-building
— is model-independent, so the scenarios become a validated suite for testing small local models. The
gate is unchanged: a proposal is only "done" at [[read-the-gate]] / [[assess-grammar]].

## Training basis

Nida (1949) — recurring partials → complementary distribution → phonological-conditioning test; Payne
(1997) on morphosyntactic description as the elicitation template. See
[../References.md](../References.md) §9, §4.
