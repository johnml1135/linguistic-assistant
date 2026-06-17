# Semantic-domain elicitation (Rapid Word Collection)

> Elicit a language's vocabulary fast by walking native speakers through ~1800 semantic domains, then
> clean up and import the result into FLEx.

**Primary tool(s):** The Combine / WeSay → FLEx (LIFT import)  ·  **Mode:** change  ·  **Stage in our loop:** scan +
propose + review  ·  **Parallel-aware:** no (monolingual elicitation; feeds the lexicon parallel-QA
later draws on)

## Goal & when it runs

Rapid Word Collection (RWC, Ron Moe's method) front-loads dictionary building: instead of harvesting
words from texts one at a time, a team of native speakers brainstorms vocabulary domain by domain.
It runs as a discrete **workshop event**, typically before or alongside text-based
[[lexeme-and-lexicon-building]], and produces the raw stock the rest of the pipeline refines.

## The human process (in FLEx today)

1. A workshop is organized around Moe's **~1800 [[semantic-domain]]s** and their guiding
   **questionnaire** (a ~250-page set of elicitation questions; the inventory behind FLEx's
   `CmSemanticDomain`).
2. Over a **two-week workshop** (typically **15–30 participants**), **teams of native speakers**
   brainstorm words for each domain; typists/elicitors enter them into **The Combine** (or,
   historically, **WeSay**) with gloss, and often audio.
3. A workshop can yield on the order of **10,000–15,000 words and idioms** *(varies widely by
   workshop, team size, and language — treat as a rough order of magnitude, not a target)*.
4. **Cleanup** in The Combine: review, deduplicate/merge, and build the orthographic inventory.
5. **Export to LIFT** and **import into FLEx** for full lexicographic development.

## How the assistant supports it

- **Propose** missing glosses, candidate [[part-of-speech]], and [[semantic-domain]] placement for raw
  entries; **dedupe** near-identical forms before LIFT import.
- **Flag thin entries** (gloss-only, no definition/POS/example) for native-speaker follow-up, and flag
  domains that look under-populated for likely **culture-specific concepts** the questionnaire missed.
- Decide **guess now / ask a speaker / defer**; **emit** `lexical/*` entry/sense ops with provenance
  ("RWC workshop, domain N") and confidence.

## Inputs

The semantic-domain questionnaire, the workshop's raw word list (The Combine/WeSay export or LIFT), the
target writing system/orthography, and the existing FLEx lexicon (to merge against).

## Primitives involved

[[semantic-domain]], [[lexical-entry]], [[sense]], [[part-of-speech]], [[writing-system]],
[[homograph-number]].

## Oracle / gold / metrics

- **Parallel-QA-style:** precision/recall of dedupe and domain-placement proposals (accepted vs
  rejected on review); thin-entry flag recall.
- **Deterministic:** imported entries are later subject to the Hermit Crab `word→gloss` golden set once
  they enter parsing, but RWC import itself is not gated by it.

## Outputs

A cleaned, deduplicated LIFT file ready for FLEx import; [[semantic-domain]] assignments; backlog flags
for thin entries, suspected typos, and missing culture-specific vocabulary.

## Pitfalls

- **Domain-boundary fuzziness**: the same word lands in several domains as separate senses — see the
  polysemy-explosion pitfall in [[sense-discovery-and-disambiguation]].
- **Missing culture-specific concepts**: a questionnaire built for one culture under-prompts another;
  flag sparse domains for targeted elicitation.
- **Typist errors**: fast entry breeds spelling slips; orthography-inventory cleanup and validity checks
  catch many ([[spell-checking-and-wordform-validity]]).
- **Deferred definitions**: glosses entered, definitions postponed — and often never returned to; track
  as a debt, not a done item.

## References

Moe (2001+) Rapid Word Collection methodology & Semantic Domains; The Combine
<https://software.sil.org/thecombine/> and WeSay; LIFT interchange format; FLEx LIFT-import docs. See
[../References.md](../References.md).
