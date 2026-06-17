# Parallel-Translation QA

> Check a translated text against its aligned source — detect missing concepts, wrong senses, and
> agreement mismatches by leaning on the source side's gold morphology, with no MT and no target parser.

**Primary tool(s):** aligned source + target in FLEx; the lexicon and Hermit Crab grammar; the
**Apertium-alignment bridge** (bidix + HC lemma analysis) for reference-finding  ·  **Mode:** mixed  ·
**Stage in our loop:** scan + propose + review  ·  **Parallel-aware:** yes (this is the core)

## Goal & when it runs

This is the headline parallel workflow. Given a target text aligned to a source (NT and parallel
literature), we surface likely problems for a human to confirm. The **key method**: the source side
(e.g. NT Greek) carries **gold morphology and known relations**, so we compare target features and
sense coverage against that backbone — we never run a syntactic parser on the target and never generate
a translation. It runs whenever a draft exists to be checked against a trusted source.

## The human process (in FLEx today)

1. Align target segments to the source; key terms are tracked much as Paratext **Biblical Terms** does
   (its **4-step process** for consistent key-term rendering — list renderings, check coverage, make
   consistent, approve — is the established prior art we complement).
2. For each source concept, the checker confirms the target renders it, consistently and with the
   intended [[sense]].
3. Feature mismatches (number, person, …) and missing renderings are caught by eye — slow and uneven.

## How the assistant supports it

- **Locate references first (the alignment substrate).** Sentences are reordered and inflected, so
  surface matching fails. For a source concept: source lemma → [[cross-lingual-sense-link]] / Apertium
  **bidix** → candidate vernacular lemma(s) → find the target token whose **Hermit Crab lemma** matches,
  *anywhere* in the sentence. Lemma-level matching survives word order and inflection; it is
  deterministic and adds no MT. No match ⇒ a candidate "missing concept." (See the
  `apertium-alignment-bridge` change.)
- **Scan** alignments and **propose** flags of three kinds: **missing concept/sense** ("source has a
  sense with no target [[lexical-entry]]"), **wrong sense** chosen for the context, and
  **agreement/feature mismatch** ("singular in source, plural here — correct?").
- For each, decide *propose a fix / ask a native speaker / defer*, and **emit** candidate
  [[lexical-entry]]/[[sense]] additions plus review flags — phrased so a non-linguist can adjudicate.
- Complements, not replaces, Paratext **Biblical Terms** 4-step key-term checking and SIL **AQuA**
  (accuracy / clarity / naturalness assessment) — both prior art, neither a syntactic parser nor MT.

## Inputs

The aligned source (with its gold morphology and key-term/relation data) and target texts, the current
lexicon, the Hermit Crab grammar for reading target [[inflection-feature]]s, and the bilingual
sense-link / bidix data (from `bilingual/*`) that drives reference-finding.

## Primitives involved

[[sense]], [[inflection-feature]], [[part-of-speech]], [[lexical-entry]], [[cross-lingual-sense-link]]
(the alignment substrate); sense choices feed [[sense-discovery-and-disambiguation]].

## Oracle / gold / metrics

- **Parallel-QA eval:** precision/recall of proposed flags (missing-concept, wrong-sense,
  feature-mismatch) against an annotated parallel set — the primary gate for this workflow.
- **Deterministic:** target feature reads must agree with the Hermit Crab `word→gloss` golden set.

## Outputs

A prioritized flag backlog (missing concept / wrong sense / feature mismatch), candidate
lexicon/sense ops, and confirmations of correctly rendered key terms.

## Pitfalls

- **No syntactic parser, no MT:** keep checks anchored to the source backbone and surface features —
  don't drift into translation or full target parsing.
- **Legitimate divergence:** a feature can differ for good linguistic reasons; **ask**, don't auto-flag.
- **Key-term over-flagging:** a source term may license several renderings (as Paratext allows) — weigh
  context before calling a sense "wrong."

## References

Paratext Biblical Terms / key-term consistency (manual.paratext.org); SIL AQuA (ai.sil.org) accuracy/
clarity/naturalness assessment as prior art. See [../References.md](../References.md).
