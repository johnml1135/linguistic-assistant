## 1. Phase 1 — HC gets phonology (text-only)

- [ ] 1.1 Add vowel/consonant natural classes to the generated HC scaffold (`research/golden/hc.py` /
  the cycle's model build), with a per-language class definition for `tur` and `hun` (front/back,
  ±round at minimum). *(Per-language classes defined in `research/cycle/phonology.py`; emitting them as
  HC NaturalClass XML + verifying the archiphoneme round-trips through `hc.exe` is deferred — needs the
  native tool to verify and is the design's open question on archiphoneme representation.)*
- [x] 1.2 Add archiphoneme + harmony-rule construction in `research/cycle/`: from a high-confidence
  `harmony_families` entry, build one archiphoneme affix plus a rule over the conditioning class.
- [x] 1.3 Gate the collapse on the existing coverage round-trip — keep only if coverage holds AND the
  affix count drops; otherwise revert and retain allomorphs. *(Offline oracle: the harmony-rule expander
  must regenerate every observed allomorph; the `hc.exe` coverage gate remains the production path.)*
- [x] 1.4 Report `enumeration_debt` change per run; add a smoke test that a known family
  (`lar`/`ler`, `nak`/`nek`) collapses without coverage loss.

## 2. The triangulate-phonology skill (text-first)

- [x] 2.1 Author `linguistics/skills/triangulate-phonology.md` (audio-optional sound deciphering) and
  index it in `linguistics/skills/README.md`.
- [x] 2.2 Wire it into the morphology/phonology workflows and the relevant meta-workflows; cross-link
  with `generalize-not-enumerate`, `propose-from-evidence`, and `read-the-gate`.

## 3. Phase 2 — audio as the feature oracle

- [x] 3.1 Add a phone→phonetic-feature mapping in `research/audio/` (review-only, provenance-bearing).
- [x] 3.2 Add a feature-confirmation report that confirms/refutes a harmony family's conditioning
  feature from phone evidence; flag conflicts.
- [x] 3.3 Replace exact-surface sample resolution with stem-aware resolution through the cycle's induced
  roots, preserving the matched/unresolved contract.
- [x] 3.4 Generalize the `triangulation` report to combine orthography + distribution + optional phones,
  with a graceful audio-absent path; add fixture-based smoke tests for the no-audio case.

## 4. Phase 3 — pronunciation promotion (human-gated)

- [x] 4.1 Add a guarded emitter for `lexical.pronunciation.create` ops (human-confirmed only) validated
  by `research/proposal/change_set.py`; carry writing system, rationale, confidence, provenance.
  *(`research/audio/promotion.py:promote_pronunciations`; `lexical.pronunciation.create` added to the
  change-set vocabulary; unconfirmed candidates emit nothing.)*
- [x] 4.2 Add the generated-surface vs recorded-pronunciation consistency check as a reviewable signal.
  *(`promotion.py:check_recorded_consistency` — reviewable flag, never an automatic edit.)*

## 5. Phase 4 — audio as a second gate

- [x] 5.1 Compare HC-generated surfaces against observed phones as an independent gate; surface
  mismatches as consistency flags (no automatic mutation). *(`promotion.py:compare_generated_to_phones`
  — review-only flag. Producing the HC-generated surface to compare needs the `hc.exe` generate path;
  that wiring is the native remainder, the comparison/metric is implemented and tested offline.)*
- [x] 5.2 Define the phone↔grapheme alignment metric and the flag-vs-noise threshold (see design Open
  Questions); document results in `research/audio/README.md` and `research/cycle/README.md`.
  *(`promotion.py:feature_mismatch_count` — vowel-feature distance + threshold.)*
