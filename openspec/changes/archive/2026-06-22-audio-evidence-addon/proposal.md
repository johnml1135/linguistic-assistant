## Why

The repo already builds Swahili, Indonesian, Tagalog, and Spanish NT text data, but pronunciation and
phonology work still depend almost entirely on orthography and manual judgment. An optional audio add-on
can enrich the same lexical/grammar loop with pronunciation evidence, misspelling clues, and opt-in
sample words without changing the rule that Hermit Crab parses text, not audio.

## What Changes

- Add an audio evidence add-on in the `research/` layer for the four targets (Swahili, Indonesian,
  Tagalog, Spanish) only. It stays secondary to the current text pipeline: no audio is assumed, and
  missing audio degrades gracefully.
- Add an audio source catalog plus availability model so the pipeline records what audio is known,
  what is absent, and what licensing or segmentation caveats apply, instead of treating audio as
  guaranteed input.
- Add an opt-in sample-word capture path so a user can nominate words of interest and carry them
  forward in the built data for later pronunciation/audio enrichment.
- Add an optional Allosaurus integration that can turn available audio into phone/timestamp evidence,
  while remaining fully skippable when Allosaurus or local audio assets are unavailable.
- Add derived evidence outputs for richer lexical work: pronunciation candidates, orthography /
  misspelling alerts, and triangulation reports that compare orthography, parallel-text evidence, and
  phone evidence.
- Keep audio strictly out of the first-class contract tier: no new `audio/*` change-set family, no
  parser input path from audio, and no claim that phone strings directly define HC phoneme features.

## Capabilities

### New Capabilities
- `audio-evidence-enrichment`: optional audio-backed enrichment over the four targets'
  (Swahili/Indonesian/Tagalog/Spanish) NT data that produces pronunciation, orthography, and
  triangulation evidence without changing Hermit Crab's text-first authority.
- `opt-in-word-sample-capture`: user-chosen sample words can be attached to the built dataset and
  carried through later enrichment/reporting steps.

### Modified Capabilities
None.

## Impact

- New code: an add-on package in `research/` for audio catalogs, opt-in sample-word manifests,
  optional Allosaurus execution, and derived evidence/report generation.
- Likely touched code: `research/datasets/ebible/` to connect the add-on to the four targets' build
  outputs, plus research/docs and linguistics docs describing pronunciation and lexical enrichment.
- Optional dependencies only: Allosaurus and local WAV conversion helpers live behind an extra; the
  core research loop stays offline-capable and green without them.
- Out of scope: any mandatory audio pipeline, any `audio/*` primary schema, direct HC
  parsing from audio, or replacing the text/parallel pipeline with speech tooling.