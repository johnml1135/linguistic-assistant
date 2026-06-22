## Context

`research/cycle/tdd.py` induces a Hermit Crab grammar from eBible wordforms under a coverage gate, and
now reports `harmony_families` + `enumeration_debt`: a sizable fraction of the kept affixes are harmony
allomorphs. The cycle cannot collapse them because the auto-generated HC scaffold has no phonology — it
assigns one symbolic feature per orthographic character and uses a single "any" natural class, so (for
Swahili height harmony) `-ish-` and `-esh-` are unrelated strings to it, not one morpheme `-Vsh-` whose
vowel is fixed by vowel-height harmony.

The `audio-evidence-addon` (already landed) yields Allosaurus phone strings as review-only evidence for
opt-in sample words on the four targets (Swahili/Indonesian/Tagalog/Spanish), but nothing consumes them:
`reports.json` is a sink. Phones are precisely the witness that orthographic distribution lacks — they
expose the phonetic feature that conditions a harmony alternation.

The repo's `pronunciation` primitive already fixes the doctrine: pronunciation/phones are *surface*
data, distinct from the phonemic underlying form HC parses; useful as a consistency check and
documentation, never as parser input. This change operationalizes that doctrine as a loop.

## Goals / Non-Goals

**Goals:**
- Make phonology expressible and inducible in the cycle (natural classes + archiphoneme harmony rules).
- Drive induction toward generalization: collapse allomorph sets when, and only when, the coverage gate
  confirms the rule (fewer affixes, no coverage loss).
- Provide a text-only path to decipher sound classes and correspondences with no audio.
- Connect optional audio as a feature-grounding and second-gate witness, triangulated with text.
- Keep audio optional and non-authoritative; keep all lexicon/feature changes human-gated.

**Non-Goals:**
- A first-class `audio/*` schema or change-set tier.
- Audio as parser input, or automatic (unreviewed) HC feature / lexicon mutation.
- A full phoneme inventory hand-authored up front — the loop induces and verifies incrementally.
- Replacing the text/parallel pipeline or the existing coverage gate.

## Decisions

### 1. Phonology lives as natural classes in the HC scaffold
Replace per-character symbols with vowel/consonant **natural classes** (e.g. front/back, ±round) in the
generated grammar, the minimum needed to write one rule over a class. Alternative: keep per-char symbols
and post-process allomorph lists. Rejected — it cannot express a generative rule, so HC can never
*verify* the generalization, which is the whole point of the engine+oracle design.

### 2. `enumeration_debt` is the optimization target, gated by coverage
The cycle proposes a collapsed archiphoneme affix + a harmony rule over the conditioning class, HC
generates the surfaces, and the change is kept **iff coverage holds and the affix count drops**. This
reuses the existing gate (`read-the-gate`) and makes Occam explicit and measurable. Alternative:
collapse by string heuristic without re-parsing. Rejected — an unverified rule parses silently wrong.

### 3. The text-only sound-deciphering path is first-class (the `triangulate-phonology` skill)
Two of the three witnesses (orthographic distribution, complementary-distribution / minimal-pair
reasoning) need no audio. The new skill captures how to infer natural classes and likely sound
correspondences from spelling alternation alone, so the loop is useful for any language on day one and
audio is purely additive. Alternative: require audio to ground features. Rejected — most fieldwork
starts text-first, and the cycle already proves harmony families are recoverable from text.

### 4. Audio is a feature-grounding witness, never parser input
When phones exist, map them to phonetic features (review-only) to **confirm or refute** a harmony
family's conditioning feature and to expose phonemic distinctions the orthography hides. Phone evidence
stays raw + provenance-bearing (unchanged from the add-on); only a derived feature-confirmation report
is added. Alternative: convert phones to HC feature bundles directly. Rejected per the add-on's own
boundary and the `pronunciation` primitive.

### 5. Three-witness triangulation; any subset is valid
Confidence comes from agreement among orthography/distribution, acoustics, and HC generation;
disagreement becomes a QA flag, not a silent choice. The triangulation MUST produce useful output with
audio absent (distribution + orthography only). This generalizes the add-on's `triangulation` report.

### 6. Sample words resolve through induced stems
Replace exact-surface matching (`word in tgt`) with resolution through the cycle's induced stems so a
sample word matches its *inflected* occurrences — the morphology the cycle exists to model. Alternative:
keep exact match. Rejected — it misses most occurrences in an agglutinative language.

### 7. Pronunciation promotion and audio-as-second-gate come last, human-gated
Only after the evidence/feature format stabilizes do we (a) promote evidence to
`lexical.pronunciation.create` ops — always via human confirmation, with rationale/confidence/provenance
like every `lexical/*` op — and (b) use observed phones as a second, independent gate (HC-generated
surface vs phone string), surfacing mismatches as consistency checks. Alternative: emit ops in v1.
Rejected — premature; the add-on deliberately deferred this (its Open Question #1).

## Phasing

The capabilities map onto four shippable phases; each emits evidence the next consumes:

1. **HC gets phonology (text-only).** Natural classes in the scaffold; archiphoneme + harmony-rule
   induction; `enumeration_debt` as the gate target. No audio. — `phonology-aware-grammar-induction`.
2. **Audio becomes the feature oracle.** Phone→feature mapping; stem-aware sample resolution; three-way
   triangulation (audio-optional). — `audio-feature-grounding`.
3. **Pronunciation promotion.** Human-gated `lexical.pronunciation.*` ops once the format stabilizes. —
   `pronunciation-evidence-promotion`.
4. **Audio as a second gate.** HC-generated surface vs observed phones, independent of the inducing
   text. — `phonology-aware-grammar-induction` (extended).

## Risks / Trade-offs

- [Over-generalized harmony rule rewrites forms it shouldn't] → keep only on coverage/golden gate with
  no regressions; prefer allomorphs + a productivity restriction over a leaky rule (`read-the-gate`,
  `generalize-not-enumerate`).
- [Single-consonant `harmony_families` over-merge distinct morphemes] → treat families as a *candidate*
  worklist for the skill/human to refine, never an auto-collapse.
- [Allosaurus emits universal phones, not language phonemes] → keep phones raw + provenance; the
  feature mapping is review-only and flagged as a hypothesis, not a phonemic claim.
- [Chapter-level Scripture audio isn't word-aligned] → acquisition stays operator-supplied or behind a
  forced-alignment extra (MFA/aeneas); never required by the text build.
- [IPA vs orthography writing-system confusion] → carry the writing system explicitly on any emitted
  pronunciation op (the `pronunciation` primitive pitfall).
- [Rule ordering / strata in HC] → test both parse and generate; a feeding/bleeding rule can pass one
  direction and fail the other.

## Migration Plan

Additive and phase-gated. Phase 1 changes only `research/cycle/` and ships independently (text-only).
Phase 2 changes only `research/audio/` + the cycle↔audio shared artifact. Phases 3–4 add a guarded op
emitter and a second gate. Existing `audio-evidence-addon` outputs and the base text build are
unchanged. Rollback per phase is trivial: revert the phase's module changes; earlier phases keep
working.

## Open Questions

- Archiphoneme representation in the HC scaffold: an underspecified segment vs a feature variable on the
  affix — which round-trips most reliably through `hc.exe`? **Answered:** an **underspecified segment**
  (vowel left unspecified for the harmonizing feature) + HC's native **alpha-variable** rule
  (`VariableFeature`/`AlphaVariable`) round-trips for both 2-way (`-lAr`) and 4-way (`-In`) harmony
  — verified in `research/cycle/hc_phonology.py` + `tests_hc.py`. Consonants need a unique identity
  feature (`cid`) so HC renders distinct morph forms.
- How much of the phoneme inventory to fix a priori per language vs induce from alternation.
- Whether to introduce a `morphophonology/*` change-set tier now for induced rules, or keep rules
  internal to the research scaffold until the format stabilizes (parallels the add-on's deferral).
- For Phase 4, the phone↔grapheme alignment metric (edit distance over features) and the threshold at
  which a generated-vs-observed mismatch becomes a QA flag vs noise.
