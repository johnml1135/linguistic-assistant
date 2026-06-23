# Skill: promote an enumerated alternation to a derived phonological rule

A morphophonological alternation is currently handled by **enumeration** (listed allomorphs / variant
affixes). Your job is to decide whether it should be **promoted** to a single derived HC `<PhonologicalRule>`
(one underlying form + a conditioning rule), and to supply the rule's form when the detector found the
family but couldn't state it. This is the judgement layer over the deterministic `review.promote` gate.

## You are given
- A candidate: its `kind` (assimilation | harmony | allomorph-collapse), the surface `members` it would
  derive, the corpus `evidence` (environment → shape distribution), and the deterministic `score`
  (conditioning sharpness × support) + whether it is `buildable` (an HC emitter exists for the kind).

## Decide + return STRICT JSON (no prose, no fences)
```json
{
  "promote": true|false,
  "underlying": "<the single underlying form, e.g. 'meN' or '-lI'>",
  "conditioning": "<one plain sentence: what environment selects which surface shape>",
  "feature": "<the phonological feature that varies: place | height | backness | rounding | voice>",
  "confidence": "high|medium|low",
  "rationale": "<one sentence>"
}
```

## Rules
- **Promote only a PREDICTABLE, COMPLEMENTARY alternation** — each surface shape in its own environment,
  the choice fully determined by an adjacent natural class (the structuralist allophone test). If the
  variants are not predictable from the environment, they are separate morphemes → do NOT promote.
- **Prefer the underlying form that makes the rule simplest** (an archiphoneme: the underspecified segment
  the rule fills in — `meN` for mem/men/meng; `-lI` for -li/-le).
- **Name the conditioning concretely** (e.g. "nasal takes the place of the following consonant: m before
  labials, n before coronals, ng before dorsals/vowels"; "suffix vowel = stem's last-vowel height").
- **Be conservative**: if the corpus support is thin, the distribution is not clean, or it is not buildable
  into a rule, return `promote:false` (it stays an enumerated allomorph / a deferral ticket for a speaker).
- You propose; the HC **round-trip** verifies (does the rule reproduce the attested members with no
  regression?). Never claim a rule that wouldn't round-trip.
