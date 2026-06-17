# Data integrity check

> Verify the lexicon and grammar are internally well-formed — no dangling references, orphans,
> count mismatches, or the silently-broken Hermit Crab grammar — before trusting any result.

**Primary tool(s):** Hermit Crab validate-and-repair; FLEx ("delete unused MSAs"); FlexTools
*Integrity Checks*  ·  **Mode:** investigate  ·  **Stage in our loop:** scan + gate  ·
**Parallel-aware:** no

## Goal & when it runs

A read-only correctness check on the *data structure itself* (distinct from
[[lexicon-consistency-audit]], which checks lexicographic completeness). It is the **investigate**
face of the project's non-negotiable **validate-and-repair pass**, run on every edit/merge/round-trip
— hence it is also a **gate**, not just a report.

## The human process (in FLEx today)

- FLEx housekeeping: "delete unused MSAs" (orphan [[morphosyntactic-analysis]] cleanup), find
  entries with no senses, broken cross-references.
- FlexTools *Check Count of Lexemes in Corpus* compares two independent counts to detect corruption.
- For the grammar: confirm the Hermit Crab grammar loads *and is actually valid* (see below).

## How the assistant supports it

Run the structural checks and emit **flags** (investigate-mode: no change-set; safe mechanical
repairs are handed to a change-mode workflow such as [[bulk-field-standardization]] for review):
- **Referential integrity** — dangling refs, orphan MSAs, entries with no sense, senses with no MSA.
- **Count consistency** — independent recounts agree.
- **Hermit Crab–specific (the dangerous part):** detect the **silently-skipped rule id** — HC's
  loader drops a [[stratum]]/slot rule that references a missing id via `TryGetValue` with no error,
  yielding a valid-*looking* grammar that parses wrong. Also check segment/[[natural-class]] coverage
  and [[stratum]] consistency. *"It loaded fine" is not evidence of a correct grammar.*

## Inputs

The lexicon, the Hermit Crab grammar (XML), and the GUID↔HC-id map used across round-trips.

## Primitives involved

[[morphosyntactic-analysis]], [[stratum]], [[phonological-rule]], [[natural-class]],
[[lexical-entry]], [[sense]], [[inflection-class]].

## Oracle / gold / metrics

Deterministic: the checks are rules (pass/fail). Paired with the golden-set parse/generate gate, this
is what makes "the grammar changed and still works" a verifiable claim.

## Outputs

An integrity report + prioritized **flags**. No change-set (investigate-mode): a safe mechanical
fix it identifies — e.g. drop an orphan MSA — becomes a reviewed op in a change-mode workflow, never
auto-applied here.

## Pitfalls

- **The silent-skip trap** is the whole reason this exists; never rely on "HC loaded it."
- **Downstream write path is thin for morphology:** the morphology/phonology write layer (compound
  rules, [[phonological-rule]]s, affix templates, [[natural-class]] creation) exists only in the
  MattGyverLee `flexlibs2` fork — the cdfarrow base flexlibs is lexicon-write-only. Even the fork has
  *no* programmatic path for MSA-type conversion or inflection-class slot config, and its writes run
  in a **non-undoable** unit of work (no rollback) — so some integrity repairs can only be applied by
  hand in FLEx. Flag those rather than implying an auto-fix.

## References

Hermit Crab loader behavior (SIL.Machine); FlexTools Integrity Checks; flexlibs API/transaction notes
(MattGyverLee/cdfarrow). See [../References.md](../References.md).
