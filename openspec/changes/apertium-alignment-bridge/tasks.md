## 1. Bilingual tier & crosswalk

- [ ] 1.1 Define the `bilingual/*` op schema (`bilingual.sense_link.add` / `.remove`): vernacular sense
  ↔ reference-language lemma+tags, with rationale/confidence/provenance. Add to the change-set contract.
- [ ] 1.2 Define the versioned **tag crosswalk** (project POS/inflection-features ↔ Apertium `sdef`),
  stored as a reviewable file; loader + validation (report unmapped tags, never drop).
- [ ] 1.3 Add a small fixture: a toy bidix + analyzed source/target sentence pair (reordered, inflected)
  for offline tests.

## 2. HC → Apertium stream adapter

- [ ] 2.1 Emit HC analyses as Apertium stream tokens `^surface/lemma<tag>…$`, tags via the crosswalk.
- [ ] 2.2 Test: round-trip a token's tags through the crosswalk (lossless for crosswalked tags).

## 3. Deterministic reference finder

- [ ] 3.1 Implement source-lemma → bidix → candidate vernacular lemma(s) → locate in target HC analyses
  (lemma+tag match, position-independent).
- [ ] 3.2 Emit located correspondences + "missing concept" when no match; never invent an alignment;
  no CG / no statistical aligner in the core path.
- [ ] 3.3 Test (fixture, no Apertium binary, no network): finds the reference under reordering+inflection;
  reports missing when absent; identical results across two runs.

## 4. parallel-translation-qa integration

- [ ] 4.1 Wire the finder in as the alignment substrate for missing-concept / wrong-sense /
  agreement-mismatch flags; located target token's HC features compared to the source backbone.
- [ ] 4.2 Confirm flags are review-only (never auto-applied) and carry confidence + provenance.

## 5. Apertium .dix export/import

- [ ] 5.1 Export an Apertium **bidix `.dix`** from the `bilingual/*` tier (derived, content-addressed;
  no `.t*x` files). Validate it parses.
- [ ] 5.2 (Optional) Export a vernacular **monodix** from lexicon + HC — gated; skip unless needed.
- [ ] 5.3 Import a FLExTrans `bilingual.dix` + sense links into `bilingual/*`; report unmappable entries.
- [ ] 5.4 Round-trip test against a FLExTrans bidix fixture (equivalent for crosswalked entries).

## 6. Optional native toolchain & docs

- [ ] 6.1 Optional `lt-proc` integration for off-the-shelf reference-language analyzers; graceful
  "unavailable" message when `lttoolbox` is absent (core stays functional).
- [ ] 6.2 README: the alignment mechanism, the sense-links-primary/`.dix`-derived rule, the FLExTrans
  boundary (no transfer rules), and the WSL/Docker note for the optional binary.
- [ ] 6.3 Obtain a real FLExTrans `bilingual.dix` sample and reconcile the layout/crosswalk for
  byte-level round-trip (coordinate, like the golden-set contract).
