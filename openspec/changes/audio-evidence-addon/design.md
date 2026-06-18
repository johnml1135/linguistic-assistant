## Context

The current research pipeline builds Turkish and Hungarian NT pair data from verse-aligned text and
derives gloss and sense-link candidates from that text-first substrate. The repo's own linguistics
docs already distinguish pronunciation/audio from the phoneme inventory Hermit Crab parses over:
audio is useful evidence and documentation, but it is not parser input and it does not define HC
feature bundles by itself.

That boundary matters here. Audio availability is uneven, licensing differs by source, and some
sources are book- or chapter-level rather than verse-level. At the same time, optional audio evidence
can still improve lexical work by enriching pronunciations, surfacing likely misspellings, and
triangulating text evidence against observed phone strings. The implementation therefore belongs in the
`research/` layer as an add-on that consumes already-built Turkish/Hungarian pair data and writes
derived artifacts back alongside it.

## Goals / Non-Goals

**Goals:**
- Add an explicit, opt-in audio enrichment workflow for the existing Turkish/Hungarian research data.
- Preserve conservative semantics: no assumption that local audio exists, no requirement that
  Allosaurus is installed, and no hard dependency from the text pipeline onto audio tooling.
- Let users nominate sample words and keep those words in the built data even before any audio exists.
- Produce reviewable derived artifacts: audio source status, sample-word matches, raw phone evidence,
  pronunciation candidates, and orthography / misspelling alerts.

**Non-Goals:**
- Finnish support.
- A new first-class `audio/*` schema or change-set tier.
- Direct HC phoneme or feature updates from Allosaurus output.
- Mandatory audio processing during the normal eBible text build.
- Automatic clip scraping/downloading from third-party sites beyond recording metadata and local file
  references supplied by the operator.

## Decisions

### 1. Separate `research/audio/` add-on package
The implementation will live in a new `research/audio/` package instead of inside the core text build
modules. This keeps the dependency boundary clear: the text pipeline stays green without audio tools,
while the add-on can evolve independently.

Alternative considered: extending `research/datasets/ebible/build.py` into a mandatory mixed text/audio
builder. Rejected because it would make optional assets and optional dependencies feel first-class.

### 2. Co-locate add-on outputs under the pair build directory
Audio-derived files will live under the existing pair output tree, for example under
`research/golden/_sources/ebible/<eng>__<tgt>/audio/`. This lets opt-in sample words become part of
the data being built up for a pair without changing the primary text contract.

Alternative considered: a separate top-level audio cache unrelated to pair outputs. Rejected because it
would split the evidence away from the lexical/parallel artifacts it is supposed to enrich.

### 3. Two explicit inputs: audio catalog and sample-word manifest
The add-on will accept:
- an audio catalog describing known sources, local asset paths, segmentation level, and license notes
- an opt-in sample-word manifest describing words the user wants tracked

Both inputs are explicit and reviewable. Missing entries mean "unknown or not provided," not failure.

Alternative considered: auto-discovering remote audio or auto-sampling words from the corpus. Rejected
because the user asked for optional, by-choice sampling and conservative assumptions about audio.

### 4. Allosaurus is wrapped as an optional evidence generator
When local audio exists and Allosaurus is available, the add-on will run it through a small wrapper
that records raw phones, optional timestamps, target inventory selection, and runtime provenance.
Results stay as evidence records only.

Alternative considered: converting Allosaurus output directly into HC phoneme or feature edits.
Rejected because phone strings are not equivalent to phonemic analysis or HC-safe feature bundles.

### 5. Derived reports are review-only
Pronunciation candidates, orthography / misspelling alerts, and triangulation summaries are derived
artifacts. They point analysts toward likely issues but do not create parser inputs, do not change the
lexicon automatically, and do not invent a first-class audio contract.

Alternative considered: emitting immediate lexical or morphophonology changes from audio evidence.
Rejected for the initial implementation because the user asked for a conservative add-on.

### 6. Sample words are preserved even when unresolved
If a chosen sample word does not resolve to the current pair data, it is still persisted with an
unresolved status. This lets the dataset carry forward analyst intent and avoids losing manually chosen
investigation targets.

Alternative considered: rejecting or dropping unresolved samples. Rejected because it hides useful
backlog signals.

## Risks / Trade-offs

- [Audio sources are missing or only loosely aligned] → Store availability and segmentation status as
  first-class metadata in the add-on output; never treat missing audio as an error in the text build.
- [Allosaurus outputs are over-interpreted as phonemes] → Persist them only as raw evidence with
  provenance and keep downstream reports review-only.
- [Misspelling heuristics produce false positives] → Emit alerts, not corrections; include the text and
  phone evidence that triggered each alert.
- [Optional dependencies complicate CI] → Put Allosaurus behind a new optional extra and keep smoke
  tests fixture-based so they run without external binaries.
- [Remote audio licensing drifts over time] → The catalog records source and license notes; the repo
  only relies on locally supplied assets during execution.

## Migration Plan

Additive only. Land docs and spec artifacts first, then the `research/audio/` package, then wire
documentation to the new command. Existing pair builds remain unchanged. Rollback is trivial: stop
invoking the add-on and ignore the derived `audio/` output folder.

## Open Questions

- Whether a later phase should add `lexical.pronunciation.*` change-set ops once the audio evidence
  format stabilizes.
- How much inventory customization to expose for Allosaurus per language in v1 versus recording only
  the default inventory provenance.
- Whether chapter-level assets need clip extraction in-repo or whether v1 should only accept already
  segmented local audio.