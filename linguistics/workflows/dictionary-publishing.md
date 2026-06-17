# Dictionary Publishing

> Turn the lexicon into a shareable dictionary — a configured view exported to Web, Word, or PDF — with
> a QA pass first so nothing unfit for publication goes out.

**Primary tool(s):** FLEx (configured dictionary views, reversal indexes) → Webonary / Word / PDF / LIFT
·  **Mode:** investigate  ·  **Stage in our loop:** review  ·  **Parallel-aware:** no (mostly lexicon-internal)

## Goal & when it runs

Publishing is the consumer-facing endpoint of [[lexeme-and-lexicon-building]]: a **configured
dictionary view** selects and formats entries, [[sense]]s, [[example-sentence]]s, and
[[reversal-index-entry|reversal indexes]] for an audience. It runs late, when the lexicon is mature
enough to share. Our value is the **QA gate** immediately before export, not the export mechanics.

## The human process (in FLEx today)

1. Choose a **Publication** (which entries/senses/examples to include) and a **Dictionary Layout**
   (how each entry is formatted) — FLEx's configured-view system.
2. Build/refresh **reversal indexes** (analysis-language → vernacular look-up) with their sort rules.
3. Export: **Webonary** (one-button direct publish since FLEx 8.3, a WordPress site at webonary.org),
   **Word** `.docx` (built-in export since FLEx 9.2, then printed/saved to PDF from Word),
   **Pathway** (the older configured-export path to PDF/OpenOffice/InDesign — now legacy/superseded by
   the built-in Word export *(deprecation status unverified)*), or **LIFT** for interchange.
4. Proofread the rendered output for missing fields, broken formatting, and sort/character errors.

## How the assistant supports it

- **Review** the publication set and **propose** fixes for gaps: missing [[sense]]/[[part-of-speech]],
  absent [[example-sentence]]s, thin glosses, inconsistent [[semantic-domain]] tagging.
- **Flag** entries unfit to publish (placeholder glosses, unverified senses, orphan reversals) and
  decide *fix now / ask a native speaker / defer past this release*.
- **Emit** `lexical/*` ops to fill gaps plus a pre-publish checklist of blocking flags; the export
  itself stays a human/FLEx action.

## Inputs

The lexicon, the chosen Publication and Layout, reversal-index configuration and sort rules, and the
target [[writing-system]]s (for special-character and collation checks).

## Primitives involved

[[lexical-entry]], [[sense]], [[example-sentence]], [[part-of-speech]], [[semantic-domain]],
[[reversal-index-entry]], [[writing-system]].

## Oracle / gold / metrics

- **Deterministic:** completeness/consistency checks against the lexicon (every published [[sense]] has
  a gloss and POS; reversals resolve) — pass/fail counts per release.
- **Parallel-QA:** not central here; coverage is measured against the publication's own inclusion rules.

## Outputs

A QA'd publication set, gap-filling lexicon ops, and a blocking-flag checklist gating the Webonary/
Word/PDF/LIFT export.

## Pitfalls

- **View-configuration complexity:** the same data renders very differently per layout — QA the
  *configured output*, not just the raw entries.
- **Export loses formatting / special characters**, and **reversal sort rules** are easy to get wrong.
- **Webonary sync cycle:** re-publishing overwrites; stage fixes before the upload, not after.

## References

FLEx "Publishing Your Data," "How to Create a Dictionary Using FieldWorks," Zook "Technical Notes on
FLEx Dictionary Printing and Export"; Webonary; LIFT. See [../References.md](../References.md).
