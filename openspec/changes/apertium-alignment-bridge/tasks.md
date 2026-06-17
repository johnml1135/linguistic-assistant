## 1. Bilingual tier & crosswalk

- [x] 1.1 Define the `bilingual/*` op schema (`bilingual.sense_link.add` / `.remove`) and add it to the
  change-set contract (`research/proposal/change_set.py` OP_TYPES + key fields).
- [x] 1.2 Define the versioned **tag crosswalk** (`research/bilingual/crosswalk.py`): project POS/features
  ↔ Apertium `sdef`; loader + report-unmapped (never drop).
- [x] 1.3 Add an offline fixture (`research/bilingual/fixtures.py`): toy bidix + reordered/inflected
  source/target streams.

## 2. HC → Apertium stream adapter

- [x] 2.1 `research/bilingual/stream.py`: parse/render `^surface/lemma<tag>…$`; `hc_analysis_to_token`
  emits HC analyses as stream tokens via the crosswalk.
- [x] 2.2 Test: tags round-trip through the crosswalk (lossless for crosswalked tags; unmapped reported).

## 3. Deterministic reference finder

- [x] 3.1 `research/bilingual/finder.py`: source lemma → bidix → candidate vernacular lemma(s) → locate
  in target HC analyses (lemma-level, position-independent).
- [x] 3.2 Emit located correspondences + "missing concept" on no match; no CG, no statistical aligner.
- [x] 3.3 Test (no Apertium binary, no network): found under reorder+inflection; missing reported;
  identical across two runs.

## 4. parallel-translation-qa integration

- [x] 4.1 `research/bilingual/qa.py`: deterministic candidate flags (missing-concept, agreement-mismatch)
  built on the finder — the alignment substrate. (Wrong-sense / confirmation is the skill layer.)
- [x] 4.2 Flags are review-only and carry confidence + provenance.

## 5. Apertium .dix export/import

- [x] 5.1 `research/bilingual/bidix.py`: export an Apertium **bidix `.dix`** from the `bilingual/*`
  sense-link tier (`sense_links.build_bidix` → `serialize_bidix`); byte-stable; no `.t*x` files.
- [ ] 5.2 (Optional) Export a vernacular **monodix** from lexicon + HC — deferred; HC→stream covers
  in-repo needs.
- [x] 5.3 `research/bilingual/flextrans.py`: import a FLExTrans `bilingual.dix` into the bidix model.
- [x] 5.4 Round-trip test (`serialize → parse` equivalence). *Byte-level reconciliation against a real
  FLExTrans sample is 6.3.*

## 6. Optional native toolchain & docs

- [ ] 6.1 Optional `lt-proc` integration for off-the-shelf reference-language analyzers (graceful
  "unavailable" when `lttoolbox` absent). *Deferred — core runs without it.*
- [x] 6.2 `research/bilingual/README.md` + README change-set tier row + the `cross-lingual-sense-link`
  primitive + `parallel-translation-qa` substrate wiring.
- [ ] 6.3 Obtain a real FLExTrans `bilingual.dix` sample and reconcile layout/crosswalk + tag direction
  for byte-level round-trip. *Cross-agent / needs a sample.*
