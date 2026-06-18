## Why

The TDD grammar cycle (`research/cycle/`) now *measures* where it is stuck: `enumeration_debt` shows
that roughly half the kept affixes are vowel-harmony allomorphs of one another (Turkish 63/124,
Hungarian 60/120 — `lar/ler`, `nak/nek`, `tól/től`…). That plateau is a **phonology deficit**: Hermit
Crab v1 has no phonology in the scaffold (one symbolic feature per orthographic character, an "any"
natural class), so it can only *list* surface allomorphs, never state the rule that generates them.

Separately, the `audio-evidence-addon` produces Allosaurus phone strings as review-only evidence — but
those phones are exactly the witness distribution-from-spelling lacks: the phonetic features
([±back], [±round]) that *condition* the harmony. The two efforts are currently disconnected.

This change makes phonology a first-class, self-supporting loop: three **independent witnesses** to the
same sound system — distribution (text-only), acoustics (optional audio), and HC generation — that
check each other. None is authoritative alone, which preserves the repo's engine+oracle discipline and
the audio add-on's "evidence, not parser input" boundary. The loop pays down the measured enumeration
debt and works with **no audio at all**, using audio only to confirm or disambiguate when present.

## What Changes

- Give the HC induction scaffold a **minimal phonology**: vowel/consonant natural classes instead of
  per-character symbols, so a single archiphoneme affix (`-lAr`) + one harmony rule can be expressed.
- Turn `enumeration_debt` from a reported metric into the cycle's **optimization target**: propose a
  collapsed archiphoneme affix + a rule over the conditioning class; accept it only if HC coverage holds
  with *fewer* affixes (Occam, gated by the existing coverage round-trip — `read-the-gate`).
- Add a **text-only sound-deciphering path** (a new skill, `triangulate-phonology`) that infers natural
  classes and likely sound correspondences from orthographic alternation and minimal pairs before any
  audio exists — so the loop is useful on day one for any language.
- **Connect the audio add-on as a feature-grounding witness**: map Allosaurus phones to phonetic
  features (review-only) to confirm/refute a harmony family's conditioning feature; resolve sample
  words through the cycle's induced stems (not just exact surface match); make `triangulation` a true
  three-way (orthography ↔ distribution ↔ phones) that degrades gracefully when audio is absent.
- Add, as a later phase, **human-gated promotion** of stabilized evidence to `lexical.pronunciation.*`
  change-set ops, and **audio as a second independent gate** (HC-generated surface vs observed phones).
- Keep every boundary the audio add-on set: no `audio/*` parser-input path, no automatic lexicon or HC
  feature mutation, audio optional throughout.

## Capabilities

### New Capabilities
- `phonology-aware-grammar-induction`: the induction cycle can express and induce natural classes +
  archiphoneme/harmony rules, gated to collapse allomorphs only when coverage holds and affix count
  drops; optional audio acts as a second, independent generation gate.
- `audio-feature-grounding`: optional phone evidence is mapped to phonetic features and triangulated
  against orthography and distribution to confirm conditioning, with the path fully functional when no
  audio is available.
- `pronunciation-evidence-promotion`: stabilized pronunciation evidence may be promoted to human-gated
  `lexical.pronunciation.*` ops, and HC-generated surfaces are checked against recorded pronunciations
  as a consistency signal — never an automatic edit.

### Modified Capabilities
None. (Builds on `audio-evidence-enrichment` / `opt-in-word-sample-capture` without changing their
contracts.)

## Impact

- New/changed code: `research/cycle/` (natural classes + archiphoneme induction + debt-as-target),
  `research/audio/` (phone→feature mapping, stem-aware sample resolution, three-way triangulation), and
  later a guarded pronunciation-op emitter validated by `research/proposal/change_set.py`.
- New knowledge artifact: `linguistics/skills/triangulate-phonology.md` (audio-optional sound
  deciphering), wired into the morphology/phonology workflows and meta-workflows.
- Optional dependencies only: Allosaurus stays behind the `audio` extra; the text-only path needs none.
- Out of scope: Finnish; a first-class `audio/*` schema; audio-driven parsing; replacing the
  text/parallel pipeline; automatic (unreviewed) lexicon or feature mutation.
