## Why

The current audio add-on can persist sample words and record whole-clip phone evidence, but it cannot
yet find likely occurrences of a target word inside longer NT audio, rank multiple candidates, or let
an analyst replay the best windows while reviewing phonology evidence. That gap keeps pronunciation and
phonology work dependent on manual searching even when local audio and aligned text anchors exist.

## What Changes

- Add an optional candidate-localization workflow that searches longer local audio assets for resolved
  sample words, records likely occurrence windows, and degrades gracefully when no searchable backend
  is available.
- Add candidate ranking that combines lexical match quality, transcript or timestamp confidence,
  anchor coverage, boundary quality, and optional phone-evidence cues useful for phonology review.
- Add persisted occurrence artifacts that store source audio location, offsets, ranking breakdown,
  surrounding context, and phonology-oriented evidence without mutating the lexicon or any database.
- Add on-demand preview playback that renders a temporary faded window from a stored occurrence and can
  play it locally when playback support is available.
- Keep permanent snippet export and any later “snip and attach” workflow out of scope for this change.

## Capabilities

### New Capabilities
- `audio-word-candidate-localization`: locate, rank, and persist likely word occurrences from longer
  local audio for prioritized sample words.
- `audio-word-occurrence-playback`: replay persisted occurrence windows with configurable padding and
  fade in or fade out for analyst review.

### Modified Capabilities
None.

## Impact

- Likely touched code: `research/audio/` contracts, orchestration, reporting, and smoke tests.
- Likely new code: backend abstraction for word-timestamp search, candidate ranking and persistence,
  preview rendering, and local playback helpers.
- Likely dependency changes: optional audio extras for a word-timestamp ASR backend and local playback,
  while keeping the base research install path unchanged.
- Constraints preserved: audio remains review-only evidence, outputs stay as plain files under the pair
  directory, and this repo still does not write directly to a database.