## Why

`parallel-translation-qa` needs to locate a source concept's realization in a target sentence that is
**not word-aligned** — word order differs and both sides are inflected. Surface-string matching fails;
full statistical alignment is heavy and nondeterministic. A **morphology-aware, deterministic
lemma-lookup-and-locate** — Hermit Crab vernacular analyses + a bilingual dictionary built from sense
links — solves it, and speaking **Apertium's `.dix` format** buys direct **FLExTrans** interoperability.
This is alignment **as input to QA, not translation generation** (which stays NLLB-200 / Serval).

## What Changes

- Add a **`bilingual/*` change-set tier**: cross-lingual **sense links** (vernacular sense ↔
  reference-language lemma), reviewable as plain text like `lexical/*`, with rationale/confidence/provenance.
- Add a **deterministic reference finder**: source lemma → **bidix** lookup → candidate vernacular
  lemma(s) → **locate** in the target via Hermit Crab lemma analyses (reorder/inflection robust) →
  feed `parallel-translation-qa` flags (missing concept / wrong sense / agreement mismatch).
- Add an **HC → Apertium stream adapter** (`^surface/lemma<tag>…$`) and a versioned **tag crosswalk**
  (our POS / inflection features ↔ Apertium `sdef` tags).
- Add Apertium **`.dix` export** (bidix from sense links; optional vernacular monodix from lexicon+HC)
  as *derived build artifacts*, and **import** of a FLExTrans `bilingual.dix` + sense links (round-trip).
- **Scope guard:** bidix + monolingual analyzers ONLY — **not** the `.t1x/.t2x/.t3x` transfer pipeline
  (that is MT, ruled out). Avoid Constraint Grammar (`cg-proc`) — nondeterministic. The Apertium binary
  is an **optional interop dependency** (native C++, Linux-first); the vernacular alignment runs
  natively without it.

## Capabilities

### New Capabilities
- `cross-lingual-alignment`: the `bilingual/*` sense-link tier + the deterministic, morphology-aware
  reference finder that locates a source concept in an unaligned target sentence and emits QA flags.
- `apertium-interop`: Apertium `.dix` export/import + the HC→stream adapter + tag crosswalk, giving
  FLExTrans direct import/export — without the transfer-rule (MT) layer.

### Modified Capabilities
<!-- None in OpenSpec specs. The linguistics workflow doc `parallel-translation-qa.md` and the
     `qa-not-mt-parallel-core` scope memory are updated alongside this change (outside openspec/specs). -->

## Impact

- **New code:** `bilingual/*` op schema; the reference-finder; the Apertium stream adapter + `.dix`
  export/import; the tag crosswalk. Python in `research/` now; a C# `Bilingual`/`Apertium` lib later.
- **Reuses:** the HC verifier (`hc` CLI), `lexical/*` change-sets, the `parallel-translation-qa`
  workflow + its parallel-QA gold, sense links.
- **External optional dep:** `lttoolbox`/Apertium (native C++, Linux-first; WSL/Docker on Windows) —
  lives in the interop tier, not the managed core loop.
- **Contracts:** the tag crosswalk + `bilingual/*` schema are aligned 1:1 with FLExTrans's Apertium
  file layout (its `bilingual.dix` is itself derived from FLEx sense links + can synthesize via HC, so
  the architectures match).
- **Out of scope:** transfer-rule (`.t*x`) generation, translation output, CG disambiguation,
  full statistical word alignment.
