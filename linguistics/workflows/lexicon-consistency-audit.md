# Lexicon consistency audit

> Scan the lexicon for completeness and consistency problems — missing fields, duplicates,
> inconsistent values — and surface them as prioritized review flags. *"See if this is healthy."*

**Primary tool(s):** FLEx; FlexTools Reports/Duplicates modules  ·  **Mode:** investigate  ·  **Stage in
our loop:** scan (→ review)  ·  **Parallel-aware:** partial

## Goal & when it runs

A read-only health check over the lexicon. It does not change anything; it produces findings the
team (or downstream change-workflows) can act on. This is the archetypal **investigate** workflow:
"see if this works / see what's wrong," as opposed to "change X to Y."

## The human process (in FLEx today)

Linguists run **FlexTools** report/check modules and read the output:
- *Lexicon Statistics* — counts of entries/senses and coverage of definitions/examples.
- *Incomplete Analyses* — corpus segments with missing morphs or senses.
- *Find Duplicate Entries* / *Find Duplicate Definitions* — candidate duplicates by matching
  headword + [[morph-type]] + [[part-of-speech]] (entries), or repeated definitions across the
  [[sense]]s of a single entry (definitions).
- Manual review of entries lacking [[sense]] glosses/definitions, [[part-of-speech]], or
  [[example-sentence]]s; spotting inconsistent glosses across similar entries.

## How the assistant supports it

- **Run the audit** and emit **review flags** (not change-sets): "entry X has no definition,"
  "senses Y and Z look like duplicates," "POS inconsistent across these near-synonyms."
- **Prioritize** by impact (frequency, publishability) and confidence, feeding the backlog.
- Decide *flag for a speaker / flag for the linguist / auto-low-priority*. Fixes are handed to the
  change-mode workflows ([[duplicate-detection-and-merge]], [[bulk-field-standardization]],
  [[sense-discovery-and-disambiguation]]), keeping investigate and change cleanly separated.

## Inputs

The lexicon (entries, senses, examples, POS, semantic domains); optionally the corpus for
usage-based prioritization; publication settings for "is this publishable yet."

## Primitives involved

[[lexical-entry]], [[sense]], [[example-sentence]], [[part-of-speech]], [[semantic-domain]],
[[homograph-number]], [[lexical-relation]].

## Oracle / gold / metrics

Investigate-mode, so no deterministic grammar gate. Quality is measured as a **parallel-QA-style
eval**: precision/recall of flagged issues against an annotated sample, plus coverage deltas
(% of entries with a definition/example/POS) tracked over time.

## Outputs

A consistency report + prioritized backlog **flags**. No change-set (fixes come from change-mode
workflows).

## Pitfalls

- **False "duplicates."** Genuine [[homograph-number|homographs]] and regular polysemy look like
  duplicates; flag, don't merge — merging is a separate, reviewed change ([[duplicate-detection-and-merge]]).
- **Coverage ≠ quality.** A filled definition field can still be wrong; coverage metrics are a floor,
  not a ceiling.
- Don't let an audit silently become an edit — investigate emits flags only.

## References

FlexTools Reports & Duplicates modules (cdfarrow/MattGyverLee); FLEx Lexicon docs; Atkins & Rundell
(2008) on entry completeness. See [../References.md](../References.md).
