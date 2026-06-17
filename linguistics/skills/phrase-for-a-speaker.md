# phrase-for-a-speaker

> Turn a linguistic question into one an *untrained* native speaker can answer — strip the jargon,
> offer concrete A/B/C choices grounded in real example sentences, and ask about meaning and
> acceptability, never about theory.

**Judgment type:** communicate  ·  **Grounded in:** Rapid Word Collection elicitation (Moe 2001+);
LAMP (Brewster & Brewster 1976); Pike (1947) monolingual demonstration  ·  **Used by:**
[[../workflows/interlinearization]], [[../workflows/sense-discovery-and-disambiguation]],
[[../workflows/parallel-translation-qa]]; the output side of [[guess-ask-or-defer]]

## The judgment

Once [[guess-ask-or-defer]] routes a decision to **ask**, this skill makes the asking *answerable*.
The whole accessibility premise — an untrained native speaker as a first-class contributor — collapses
if the question arrives as *"is the plural allomorph phonologically conditioned?"* A speaker cannot
answer that, but they can instantly answer *"which sounds right: `kitabu` or `kitabi`?"* The judgment
is translation: from the linguist's analytic frame into the speaker's lived competence — their sense
of what *means what* and what *sounds right*.

Three moves do the work: **strip the jargon** (no "morpheme", "stratum", "MSA"); **make it concrete**
(present 2–3 candidate forms, a minimal pair, or A/B/C glosses, grounded in a real
example sentence or context the speaker recognizes); and **ask about meaning or acceptability, not
theory** (*"does this word fit here?"*, *"are these the same meaning or different?"* — never *"what
inflection class is this?"*).

## Heuristic / procedure

```
Given a question to put to a speaker:
1. Restate it as a choice the speaker can hear/feel:
   ├─ acceptability  → "Which sounds right: X or Y?" (offer a MINIMAL PAIR)
   ├─ meaning/sense  → "Same meaning or different?" with two real example sentences
   └─ usage/gloss    → A / B / C concrete options, each in a full sentence
2. Strip every technical term; substitute the speaker's own words/examples.
3. Ground in a CONTEXT the speaker recognizes (a sentence, a scene, a story).
4. Balance the options + always add an escape hatch: "none of these / something else?"
5. Avoid leading: don't signal the expected answer by order, emphasis, or framing.
```

## Inputs → outputs

- **In:** a linguistic question + its candidate answers and supporting examples, handed over by
  [[guess-ask-or-defer]].
- **Out:** a speaker-ready prompt — plain-language, with 2–3 concrete grounded options and a "none of
  these / other" path — plus a note of which underlying decision each answer resolves, so the reply
  feeds straight back into the originating workflow.

## Interaction with other skills & the gate

This is the realization of the **ask** branch of [[guess-ask-or-defer]]. The speaker's answer becomes
fresh evidence for [[propose-from-evidence]] or [[divide-senses]], and any resulting change still must
clear [[read-the-gate]] — a speaker's *"X sounds right"* raises confidence but does not bypass the
golden-set round-trip.

## Failure modes / guardrails

- **Leading questions** — order, emphasis, or a single-option framing biases the answer; offer
  balanced options and never telegraph the "expected" one.
- **No escape hatch** — forcing a choice among wrong options manufactures false data; always allow
  "none of these / other".
- **Smuggled jargon** — a single technical word ("affix", "tense") can make the question unanswerable;
  test every prompt against *"would a speaker with no training understand this?"*
- **Ungrounded abstraction** — words judged out of context get unreliable answers; anchor in a real
  sentence or scene.

## Training basis

Concrete, context-grounded, meaning-first elicitation is the core of Rapid Word Collection (Moe
2001+) and LAMP (Brewster & Brewster 1976); Pike's (1947) monolingual demonstration shows how far
analysis can go on acceptability judgments alone, with no shared metalanguage. See
[../References.md](../References.md) §9, §1.
