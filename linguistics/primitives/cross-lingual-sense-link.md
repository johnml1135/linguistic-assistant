# Cross-lingual sense link

> A link from a vernacular [[sense]] to a reference-language lemma/sense — the atom of bilingual
> alignment and the source from which an Apertium bilingual dictionary is derived.

**LibLCM class:** *none native* (FLExTrans convention over `LexSense` + custom fields)  ·  **FLEx UI:**
FLExTrans "Sense Linker"  ·  **Tier:** bilingual  ·  **In MiniLcm:** no

## What it is (linguistics)

A cross-lingual sense link records that a vernacular meaning corresponds to a meaning in a
reference/source language (English, Spanish, NT Greek, …). It is **not** a translation rule and **not**
a lexical relation *within* one language ([[lexical-relation]]) — it is a bilingual correspondence at
the sense level. Its purpose here is **alignment**: given a source concept, the link tells us which
vernacular lemma realizes it, so we can find that concept in an imperfectly-aligned target sentence.

## How LibLCM models it

LibLCM has **no first-class bilingual-link class**. FLExTrans stores sense links over the FLEx data
(via `LexSense` references / custom fields) and derives an Apertium `bilingual.dix` from them. So a
sense link is FLExTrans-convention, not a core FieldWorks object — which is exactly why, in this repo,
it lives in its **own `bilingual/*` change-set tier** rather than `lexical/*`.

## Hermit Crab mapping

Indirect. HC analyzes the *vernacular* token to a lemma + features; the sense link maps that lemma to
the reference lemma. HC analyses are emitted in **Apertium stream format** (`^surface/lemma<tag>…$`) so
the vernacular side joins the bidix world *through HC*, without a second vernacular morphology. See the
`apertium-alignment-bridge` change.

## In our change-sets

A `bilingual/*` op, reviewable as plain text:

```yaml
op: bilingual.sense_link.add
vernacular_sense: { entry: "kondoo", sense: 1 }   # 'sheep/shepherd'
reference_lemma: { lang: "eng", lemma: "shepherd", pos: "n" }
rationale: "aligns MRK 6:34 source 'shepherd' to kondoo-1"
confidence: 0.7
provenance: { ref: "MRK 6:34" }
```

The Apertium **bidix `.dix`** is *generated from* these links (a derived build artifact, never
hand-edited) — mirroring how the HC grammar XML is an artifact of the morphology change-sets.

## QA & parallel relevance

This is the alignment substrate for [[../workflows/parallel-translation-qa]]: source lemma → sense link
/ bidix → candidate vernacular lemma → locate via HC analysis → check the concept is present and its
features agree. Missing link / no match ⇒ a "missing concept" flag. Lemma-level matching survives word
order and inflection. Strictly **input to QA** — never translation output (that is NLLB/Serval).

## Pitfalls

- **Not a transfer rule.** Sense links + bidix are alignment only; the `.t1x/.t2x/.t3x` transfer/MT
  layer is out of scope.
- **Ambiguity.** One source lemma may link to several vernacular senses — keep all candidates and let
  the QA check / a human adjudicate; don't silently pick one.
- **No LibLCM home.** Treat sense links as our primary `bilingual/*` data; the `.dix` is derived.

## Related & references

[[sense]], [[part-of-speech]], [[inflection-feature]], [[lexical-relation]];
[[../workflows/parallel-translation-qa]]. FLExTrans (Lockwood); Apertium bidix; see
[../References.md](../References.md) §1.
