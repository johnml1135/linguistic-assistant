## Context

The current `research/audio/` add-on can persist resolved sample words, record source availability,
run optional Allosaurus recognition over operator-supplied clips, and derive review-only phonology
reports. It does not yet bridge the biggest operational gap for NT audio: locating likely word
occurrences inside longer chapter- or book-level local audio, ranking multiple candidate windows, and
letting an analyst replay those windows without manually scrubbing through the source file.

This change extends the existing add-on rather than creating a parallel subsystem. It must preserve the
same boundaries as the current audio layer: the four targets (Swahili/Indonesian/Tagalog/Spanish) only, local assets only, plain-file
outputs under the pair directory, and no direct database or lexicon mutation. The user also asked to
leave permanent snippet attachment for a later phase, so v1 needs location metadata and review
playback, not durable extracted-word assets.

## Goals / Non-Goals

**Goals:**
- Add an optional workflow that searches longer local audio for prioritized sample words and persists
  ranked occurrence candidates.
- Reuse the existing pair data and catalog inputs so candidate search is anchored to the same sample
  resolution and text references already produced by the add-on.
- Store reviewable occurrence metadata that is useful for phonology work: offsets, context words,
  lexical match kind, backend provenance, ranking breakdown, and optional phone-level cues.
- Support on-demand playback of any stored occurrence with configurable padding and fade in or fade
  out, without requiring permanent clip export.
- Keep the implementation testable offline by using injected fake backends in smoke tests and making
  all heavyweight tooling optional.

**Non-Goals:**
- Permanent snippet extraction or attaching audio directly to a downstream database.
- Automatic download of NT audio from remote sources.
- Expanding the audio scope beyond the four targets (Swahili, Indonesian, Tagalog, Spanish).
- Treating ASR or phone evidence as parser-authoritative.
- Solving all input formats in v1; preview playback will target local WAV assets first and degrade
  clearly when the source format cannot be previewed.

## Decisions

### 1. Add a separate occurrence-localization workflow inside `research/audio/`
The new behavior will live alongside the existing enrichment flow as new modules for search,
occurrence persistence, ranking, and playback. The top-level `run.py` will stay focused on whole-pair
enrichment; candidate localization and playback will have their own functions and CLI entrypoints.

Alternative considered: folding candidate search into the existing `run_enrichment` loop. Rejected
because localization and playback have different runtime costs, dependencies, and operator intents than
whole-pair evidence generation.

### 2. Use a backend abstraction with `faster-whisper` as the v1 automatic locator
The v1 implementation will define a word-timestamp backend interface and ship one concrete backend that
wraps `faster-whisper`. It is open source, exposes per-word start/end/probability fields, and is more
compatible with this repo than a torch-heavy stack. The backend remains optional; if the package or
model is unavailable, the workflow records that status and stops short of candidate generation.

Alternative considered: WhisperX as the primary backend. Rejected for v1 because it pulls in a heavier
PyTorch and alignment stack than this research add-on needs. Alternative considered: Montreal Forced
Aligner as the primary backend. Rejected because it requires language-specific dictionaries and aligned
transcripts that are not guaranteed to exist for every local asset, though the backend interface should
leave room for a later MFA import path.

### 3. Drive search from resolved sample words and eligible catalog entries
Candidate localization will start from persisted sample words and their resolved refs. It will search
only catalog entries whose target matches and whose `text_anchor` plausibly covers one of the sample's
refs or declared ref. For verse-level assets this is exact; for chapter- and book-level assets the
workflow searches the full file but records the broader anchor provenance.

Alternative considered: transcribing every local asset and only later matching sample words. Rejected
because it is expensive, harder to explain, and does not use the anchor data already present in the
repo.

### 4. Persist occurrence records as reviewable JSON under the pair directory
The workflow will write `word_occurrences.json` under the pair's `audio/` folder. Each occurrence will
have a stable ID plus source path, source ID, text anchor, start/end offsets, preview defaults,
matched token, sample word, lexical match kind, score, score breakdown, surrounding transcript words,
and provenance. Optional phonology cues will include candidate-local phone evidence, mapped vowel
features, and any conditioning or triangulation summaries derived from them.

Alternative considered: storing only the top-ranked hit per word. Rejected because analysts need to
compare alternates and later phases may want to promote multiple stored candidates into attachment
workflows.

### 5. Rank conservatively and expose the breakdown
Ranking will combine several transparent signals: exact-normalized match over stem-aware match, backend
word probability, anchor specificity, boundary cleanliness from neighboring word gaps, duration sanity,
and optional phonology usefulness such as recoverable vowel phones. The total score and component
scores will be stored so analysts can understand why a candidate outranked another.

Alternative considered: a learned reranker. Rejected because the repo has no gold set for this task and
the user asked for a reliable, inspectable workflow.

### 6. Playback renders temporary previews from stored offsets
Playback will not depend on permanent snippet storage. Instead it will read the source WAV, apply
configurable pre/post padding and linear fades, emit a temporary preview WAV, and play it through a
platform-native mechanism when available. On Windows, `winsound` is sufficient for WAV playback; other
platforms can use lightweight subprocess fallbacks when present. If no local player is available, the
workflow still renders the preview and returns its path.

Alternative considered: introducing a dedicated playback dependency for all platforms. Rejected for v1
to keep the add-on lighter and because temporary WAV previews plus platform-native playback satisfy the
immediate review need.

## Risks / Trade-offs

- [ASR misrecognizes low-resource or inflected forms] → Keep candidates review-only, store alternates,
  and prefer transparent ranking over automatic acceptance.
- [Chapter-level search returns too many weak matches] → Restrict search to sample-driven eligible
  catalog entries and score exact-normalized matches above stem-aware matches.
- [Playback fails for non-WAV local assets] → Record a clear unsupported-format status and keep stored
  offsets so later phases can add transcoding or permanent extraction without losing localization work.
- [Heavy model downloads or missing runtime slow adoption] → Keep the backend optional, make smoke
  tests dependency-free via injection, and report unavailability rather than failing the add-on.
- [Phone evidence from tiny windows is noisy] → Treat phone cues as additive ranking context and
  provenance-bearing evidence, never as parser input or an acceptance criterion by itself.

## Migration Plan

Additive only. Introduce new contracts, search/ranking/playback modules, and a new occurrence artifact
under existing pair `audio/` outputs. Update the audio docs and optional dependencies. Existing sample
resolution and whole-clip evidence workflows remain unchanged. Rollback is trivial: stop invoking the
candidate workflow and ignore `word_occurrences.json` plus preview playback commands.

## Open Questions

- Whether a later phase should add an MFA-backed alignment importer for projects with known transcripts
  and pronunciation dictionaries.
- Whether preview rendering should eventually support MP3 or other compressed local assets in-repo, or
  require operator conversion to WAV before localization and playback.
- How many top candidates per word should be promoted by default into a future “snip and attach” flow.