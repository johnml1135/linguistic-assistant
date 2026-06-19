# triangulate-phonology

> Decide which symbols are the *same sound* and which **contrast** — the phoneme inventory and
> [[../primitives/natural-class]]es — from whatever witnesses you have: orthographic distribution and
> alternation (**always, no audio needed**), and phone evidence (when audio exists). This is the
> feature-grounding step that [[generalize-not-enumerate]] needs before it can write a rule.

**Judgment type:** decide (+ propose)  ·  **Grounded in:** phonemic analysis — complementary
distribution & minimal pairs (Pike 1947; Nida 1949; Hockett 1955); SPE natural classes (Chomsky &
Halle 1968); the practical-orthography ≈ phonemic relationship (field practice)  ·  **Used by:**
[[../workflows/morphological-parser-setup]], [[../workflows/interlinearization]],
[[../meta-workflows/bootstrap-a-new-language]], [[../meta-workflows/steady-state-virtuous-cycle]],
[[../meta-workflows/test-a-grammar-theory]]; feeds [[generalize-not-enumerate]]

## The judgment

[[generalize-not-enumerate]] collapses `-lar/-ler` into one rule **over a natural class** — but only if
the class exists. *Which symbols belong in the class?* is this skill's job. It is the classic phonemic
question — *are these two sounds the same phoneme or two?* — answered with the evidence a bootstrap loop
actually has, which is usually **text first, audio later or never**.

The key realization: **a practical orthography is itself a (lossy) phonemic transcription.** You do not
need a microphone to start. Most of the work — deciding that ⟨a⟩ and ⟨e⟩ are the two faces of one
suffix vowel, that ⟨ı i u ü⟩ pattern as a four-way harmony set, that ⟨k⟩ and ⟨g⟩ contrast — is
**distributional reasoning over spelling**. Audio, when present, *confirms which feature* drives the
class and *catches where the spelling lies*; it is the third witness, not the first.

## Heuristic / procedure

Goal: which symbols realize one phoneme (→ a class / archiphoneme), and which contrast (→ separate
phonemes)?

```
1. GATHER the witnesses you actually have:
   - orthographic distribution (ALWAYS): each symbol + the slot/environment it appears in
   - alternation sets: harmony families (research/cycle `harmony_families`), zero-parse clusters
   - phone evidence (IF audio): Allosaurus phones per word — review-only

2. TEXT-ONLY deciphering (no audio required):
   ├─ Complementary distribution? Two symbols never contrast in the same environment and one is
   │     selected by context → candidate ALLOPHONES of one archiphoneme (not a contrast).
   ├─ Minimal pair? Two words differ in exactly one symbol AND in meaning → that symbol is
   │     CONTRASTIVE (a separate phoneme); do NOT fold it into a class.
   ├─ Shared alternation skeleton? The symbols that alternate in one morpheme slot ARE the
   │     conditioning class (e.g. {a,e} backness; {ı,i,u,ü} backness×rounding).
   └─ Read the orthography's design: digraphs, diacritics, and predictable spelling rules already
         name classes and allophony — use them as a prior, not gospel.

3. AUDIO grounding (only if phones exist): map phones → phonetic features, then
   ├─ NAME the feature that conditions a text-found class (is a/e split [±back] or [±round]?), and
   └─ CATCH orthography lies: underdifferentiation (1 grapheme = 2 phones → a hidden contrast) or
         overdifferentiation (2 graphemes = 1 phone → a spelling, not a sound, distinction).

4. TRIANGULATE: agreement across witnesses → propose the class / inventory entry with higher
   confidence; conflict → record a QA flag and lower confidence. Any single witness alone is weak.

5. VERIFY (never assume): hand the proposed class to [[generalize-not-enumerate]] → HC generates the
   surfaces → [[read-the-gate]]. Keep the class/inventory change only if it survives the round-trip.
```

## Inputs → outputs

- **In:** wordforms with per-slot symbol distribution; alternation sets (harmony families / zero-parse
  clusters); the current partial phoneme inventory; *optionally* phone evidence (`research/audio/`).
- **Out:** proposed [[../primitives/natural-class]]es / phoneme-inventory entries (with the conditioning
  feature when known), each tagged with **which witnesses agreed** + confidence + provenance; or a
  `guess-ask-or-defer` outcome — *defer / get audio / ask a speaker* — when the text witnesses conflict
  and no audio resolves them.

## Interaction with other skills & the gate

This is **upstream of [[generalize-not-enumerate]]**: it supplies the class that the rule generalizes
over (the flagship skill even notes it must "propose the natural class too" — this is how). It consumes
[[propose-from-evidence]]'s alternation clusters, routes uncertainty through [[guess-ask-or-defer]] (and
[[phrase-for-a-speaker]] when a minimal-pair judgement needs a speaker's ear), and every proposed
class/inventory change is bounded by [[read-the-gate]] — a wrong inventory makes the whole grammar
parse silently wrong, so the gate is non-negotiable.

## Failure modes / guardrails

- **Trusting the orthography too far.** Practical spellings under-differentiate (one letter, two
  phonemes), keep historical/etymological spellings, and use digraphs — so spelling distribution is a
  strong *prior*, not proof. Flag suspected under/over-differentiation for audio or a speaker.
- **Allosaurus phones ≠ phonemes.** Allosaurus emits *universal* phones; `lang_id` narrows but does not
  phonemicize. Treat the phone→feature mapping as a hypothesis with provenance, never a phonemic claim
  or an HC feature edit (the `pronunciation` primitive boundary).
- **Allophony mistaken for contrast (or vice versa).** Complementary distribution = one phoneme;
  contrast in identical environments = two. Conflating them either invents spurious classes or misses
  real ones.
- **One-witness confidence.** A class seen only in spelling, or only in audio, is low-confidence until a
  second witness or the HC gate agrees. Record which witnesses concurred.
- **Premature inventory from sparse data.** A handful of forms can fake complementary distribution;
  require enough environments, or defer.

## From practice (the TDD cycle on Swahili)

`research/cycle/` recovers harmony families **from spelling alone** — `harmony_families()` groups
affixes by consonant skeleton (Swahili verb extensions: `sh=isha/esha` causative, `k=ika/eka` stative)
with no audio whatsoever, and `enumeration_debt` counts the redundant allomorphs. That is this skill
working text-only: each such family is a height-harmony class ({i,e}) waiting to be named. The limits
are the "orthography is a lossy prior" failure mode: all-vowel extensions (the applicative `-i-/-e-`)
have no consonant skeleton to anchor on, and a bare single-consonant skeleton can **over-merge**
distinct morphemes — exactly where audio or a speaker earns its keep. The hand-off is clean: this skill
names the class, audio (via `research/audio/`, confirming the `high` feature) grounds it,
[[generalize-not-enumerate]] writes the rule, and the coverage gate keeps it only if it survives.

## Training basis

Pike (1947) and Nida (1949) on phonemic discovery (complementary distribution, minimal pairs); Hockett
(1955) on the phoneme; SPE (Chomsky & Halle 1968) and Kenstowicz (1994) on natural classes and
features. See [../References.md](../References.md) §3 (phonology & morphophonology), §4 (field methods).
