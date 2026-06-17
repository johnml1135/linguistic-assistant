## Context

`parallel-translation-qa` (linguistics workflow) checks a target text against a source backbone for
missing concepts, wrong senses, and agreement mismatches. It assumed aligned input, but real parallel
literature (NT + similar) is reordered and inflected on both sides — surface matching can't locate "is
the concept *shepherd* here, and is its number right?" The repo already has HC as the authoritative
vernacular analyzer (`hc` CLI, `hermitcrab-net-verifier`), a two-tier change-set (`lexical/*` +
`morphophonology/*`), and sense links as the FLEx-native cross-lingual datum. FLExTrans already derives
a `bilingual.dix` from FLEx sense links and can synthesize via HC — so its architecture matches ours.

The earlier scope decision (`qa-not-mt-parallel-core`) ruled Apertium *out as MT*. This change adds a
**narrow, principled exception**: Apertium's analyzer + bidix as an alignment/interop layer — input to
QA, never translation output.

## Goals / Non-Goals

**Goals:**
- A deterministic, morphology-aware **reference finder** that locates a source concept in an unaligned
  target sentence (lemma+tag match via bidix + HC analyses), feeding `parallel-translation-qa`.
- A reviewable **`bilingual/*` sense-link tier**; Apertium `.dix` as *derived* artifacts.
- **FLExTrans direct import/export** for bidix + sense links + lexicon/monolingual data.
- Keep the Apertium binary **optional**; core works natively/offline.

**Non-Goals:**
- Translation generation, `.t*x` transfer-rule generation, Constraint Grammar, full statistical word
  alignment, a second vernacular morphology, C# port (later).

## Decisions

- **Alignment by targeted lemma-lookup-and-locate, not full alignment.** We don't need a complete word
  alignment — only to find *a specific source concept's* target realization. source lemma → bidix →
  candidate vernacular lemma(s) → match target tokens' HC lemmas. *Alternative:* fast_align/GIZA on
  morph-annotated text (Apertium's documented path) — heavier, statistical, nondeterministic; rejected
  for the core (could be an optional enrichment later).
- **HC stays the only vernacular morphology; Apertium is the bilingual layer.** Bridge via the
  **Apertium stream format** (`^surface/lemma<tags>$`) emitted from HC. *Alternative:* generate a
  vernacular Apertium monodix and analyze with `lt-proc` — rejected as the primary path (two
  morphologies drift); kept as an *optional export* for FLExTrans/off-the-shelf tooling.
- **Sense links primary; `.dix` derived.** Mirrors "HC grammar XML is a build artifact; the change-set
  is the source." *Alternative:* treat `.dix` as primary — rejected (hand-edited bidix can't be
  reviewed/merged like typed ops, and FieldWorks has no LibLCM home for it).
- **Avoid Constraint Grammar.** Research confirms `lt-proc`/bidix are deterministic but `cg-proc` is
  not — so the core path uses analysis + bidix only.
- **Apertium binary optional.** `.dix` is just XML we can read/write natively; HC does vernacular
  analysis; off-the-shelf reference-language analyzers (`apertium-eng`, …) and FST compilation are the
  only features that need the native (Linux-first) toolchain. *Rationale:* keep the managed core loop
  free of a native C++ dep; this layer is interop/research-tier.
- **Tag crosswalk is an explicit contract** (project POS/features ↔ Apertium `sdef`), shared by the
  stream adapter and `.dix` export/import, aligned to FLExTrans conventions.

## Risks / Trade-offs

- **Apertium is native C++, Linux-first** → keep it optional; core (sense links, `.dix` read/write,
  HC→stream, fixture finder) runs without it; Windows uses WSL/Docker only for the optional analyzer.
- **Bidix coverage gaps / lemma ambiguity** → the finder reports "not found" (candidate missing concept)
  rather than guessing; multiple bidix candidates are all checked, flagged for human review.
- **Crosswalk drift vs FLExTrans tag conventions** → version the crosswalk; round-trip test against a
  FLExTrans `bilingual.dix` fixture; report unmappable tags instead of dropping them.
- **Scope creep back toward MT** → the spec forbids `.t*x` generation and translation output; the
  workflow doc and memory record the boundary.

## Migration Plan

Additive. Land the `bilingual/*` schema + tag crosswalk + HC→stream adapter + the fixture-based finder
(CI-green, no native dep) first; then `.dix` export/import; then optional off-the-shelf-analyzer
enrichment behind the optional binary. Wire the finder into `parallel-translation-qa` as its alignment
substrate. No rollback needed (new tier + new modules).

## Open Questions

- Exact FLExTrans `bilingual.dix` + sense-link on-disk layout to target for byte-level round-trip
  (obtain a real sample; coordinate as with the golden-set contract).
- Whether the optional vernacular **monodix** export is worth maintaining, or HC→stream suffices for all
  in-repo needs (lean: HC→stream; monodix only if a FLExTrans workflow demands a compiled vernacular FST).
- Reference-language analyzer sourcing per target project (which `apertium-xxx` packages, versions).
