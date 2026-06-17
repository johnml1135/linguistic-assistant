# prioritize-the-backlog

> Rank open issues by **impact × confidence** so the loop always works the highest-value item next.

**Judgment type:** prioritize  ·  **Grounded in:** Zipf / core-vocabulary coverage (a few forms cover
most tokens)  ·  **Used by:** the scan→work ordering of every meta-workflow — explicitly
[[../meta-workflows/steady-state-virtuous-cycle]] and [[../meta-workflows/build-the-lexicon]]

## The judgment

A scan produces more candidate work than any pass can do. This skill is the *ordering* judgment: given
a backlog of zero-parses, missing senses, and integrity flags, decide **what to work first**. The rule
is **impact × confidence** — high impact alone isn't enough if the evidence is too thin to commit, and
strong evidence on a rare form isn't worth a senior linguist's first hour. Impact is dominated by
**frequency**: by Zipf's law a small head of forms covers most of the corpus, so fixing one
high-frequency parse failure can unblock thousands of tokens — Nation-style lexical-coverage research
finds the top ~2k word families cover on the order of 80–90% of running text (≈95% by ~3k). *(coverage
figures are rules-of-thumb from English/L2 studies, corpus- and language-dependent — unverified for any
specific language)*

## Heuristic / procedure

```
For each backlog item, score:
  IMPACT     = token/type frequency (from [[../workflows/corpus-coverage-and-frequency]])
             × publishability (does it block a dictionary/text deliverable?)
             × unblock-count (how many other items does fixing it enable?)
  CONFIDENCE = evidence strength (recurrence, parallel support, prior from [[introspect-typology]])

  PRIORITY   = IMPACT × CONFIDENCE

Then:
  ├─ high impact + high confidence → DO NOW
  ├─ high impact + low confidence  → gather evidence / [[guess-ask-or-defer]] (don't guess on a high-blast-radius item)
  ├─ low impact  + high confidence → batch as quick wins
  └─ low impact  + low confidence  → defer / leave a flag
Re-rank every pass.
```

## Inputs → outputs

- **In:** the current backlog (zero-parse clusters, sense gaps, integrity flags) + frequency counts
  from [[../workflows/corpus-coverage-and-frequency]] + per-item confidence from the proposing skill.
- **Out:** a ranked work queue with a one-line *why-this-rank* per item (impact factors and confidence
  named), consumed at the top of every meta-workflow's scan→work cycle.

## Interaction with other skills & the gate

It sits between the scan and the work: it does not propose or commit anything itself. It consumes
confidence from [[propose-from-evidence]] / [[divide-senses]] / [[generalize-not-enumerate]] and
priors from [[introspect-typology]], and routes low-confidence-but-high-impact items to
[[guess-ask-or-defer]] rather than to a risky commit. Items it ranks are still individually disposed
by [[read-the-gate]].

## Failure modes / guardrails

- **Stale frequencies.** Coverage shifts as the lexicon grows — **re-rank each pass**; today's head is
  tomorrow's done.
- **Small / biased corpus.** Frequency from a tiny or single-genre corpus (e.g. one Scripture book)
  skews the head; flag the caveat and don't over-trust raw counts.
- **Ignoring unblock-count.** A medium-frequency form that gates a whole paradigm or affix template can
  outrank a more frequent isolated word — count downstream unblocks, not just tokens.
- **Confidence laundering.** Don't let high impact inflate a weak-evidence item into "DO NOW"; that's
  what the ×confidence term and the [[guess-ask-or-defer]] branch are for.

## Training basis

Zipf's law and Nation-style lexical-coverage research (a small set of high-frequency word families
covers the bulk of running text); core-wordlist seeds (Swadesh, Leipzig–Jakarta, SILCAWL) as the
frequency backbone for a cold start. See [../References.md](../References.md) §9, §10.
