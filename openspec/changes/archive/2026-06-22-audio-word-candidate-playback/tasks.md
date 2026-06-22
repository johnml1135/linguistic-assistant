## 1. Candidate contracts and backend scaffolding

- [x] 1.1 Extend the audio contracts with persisted occurrence, ranking, and playback-result records.
- [x] 1.2 Add a word-timestamp backend abstraction plus an optional `faster-whisper` implementation that degrades gracefully when unavailable.

## 2. Candidate localization and ranking

- [x] 2.1 Implement sample-driven catalog selection and transcript-word matching for eligible local audio assets.
- [x] 2.2 Implement conservative candidate ranking and persist `word_occurrences.json` under the pair `audio/` directory.
- [x] 2.3 Add optional candidate-level phonology cues that attach review-only phone and feature summaries when available.

## 3. Preview rendering and playback

- [x] 3.1 Implement temporary preview rendering from stored occurrence offsets with configurable padding and fade in or fade out.
- [x] 3.2 Implement on-demand local playback with platform-native fallbacks and explicit playback-unavailable status reporting.

## 4. Workflow integration, docs, and verification

- [x] 4.1 Add CLI or entrypoint support for candidate localization and playback without disturbing the existing enrichment flow.
- [x] 4.2 Update the research audio docs and optional dependencies for the new workflow and its constraints.
- [x] 4.3 Add smoke tests for backend unavailability, ranked occurrence persistence, preview rendering, and playback fallback behavior.