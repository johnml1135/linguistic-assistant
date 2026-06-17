# Sense

> One meaning of an entry — the unit that carries a gloss, a definition, examples, semantic domains,
> and the grammatical analysis (MSA) that meaning is parsed under.

**LibLCM class:** `LexSense`  ·  **FLEx UI:** "Sense" (numbered 1, 2, 3 … under an entry)  ·  **Tier:** lexical  ·  **In MiniLcm:** yes

## What it is (linguistics)

A polysemous word has several related meanings; each is a **sense**. English *head* has senses 'body
part', 'leader', 'top of a beer', 'front of a queue'. A [[lexical-entry]] owns an ordered list of
senses; the first is the **primary** sense. Two display fields recur and are easy to confuse:
- **Gloss** — a *short* one- or two-word equivalent in the analysis language (e.g. *head*), used in
  interlinear glossing ([[interlinearization]]) and conforming to the Leipzig Glossing Rules.
- **Definition** — a *fuller* explanatory paragraph (e.g. "the part of the body containing the brain
  …"). A gloss is a label; a definition explains.

Senses nest: a **subsense** is a finer reading under a sense (e.g. *head* 'leader' → 'head of state').

## How LibLCM models it

`LexSense` is owned by `LexEntry.Senses` (an owning **sequence** — order is meaningful, first =
primary). Key properties:
- **`Gloss`** — `MultiUnicode` (per analysis [[writing-system]]); short, plain text.
- **`Definition`** — `MultiString` (formatted, multilingual); the fuller explanation.
- **`Senses`** — an owning **sequence** of `LexSense`: subsenses, recursively.
- **`MorphoSyntaxAnalysis`** — an **atomic reference** to an MSA ([[morphosyntactic-analysis]]); this
  is how [[part-of-speech]] reaches a sense (via the MSA, never directly).
- **`Examples`** — owning sequence of [[example-sentence]] (`LexExampleSentence`).
- **`SemanticDomains`** — reference collection to [[semantic-domain]] (`CmSemanticDomain`).

Other fields: `UsageNote`, `Exemplar`, `Restrictions`, `Status`, `Pictures`, and assorted notes.

## Hermit Crab mapping

HC parses and generates over [[morphosyntactic-analysis]] (category/features) and forms, not over
human-readable senses. A sense's grammatical content reaches HC *through* its MSA; the gloss and
definition are documentation HC ignores. Round-trip: the parse output names the entry+MSA, and the
gloss is what surfaces in an interlinear line.

## In our change-sets

Adding or refining a sense is a `lexical/*` op owned under an entry:

```yaml
op: lexical.sense.create
entry: "kufamba"
gloss: { en: "walk" }
definition: { en: "to move on foot at a normal pace" }
semantic_domains: ["7.2.1.1"]
rationale: "Corpus shows a motion reading not covered by existing sense 1."
confidence: 0.68
provenance: { corpus: "mark", refs: ["MRK 1:16"] }
```

Ops carry rationale/confidence/impact/provenance.

## QA & parallel relevance

The most common parallel check is **missing-sense**: a source concept has no matching sense in the
target lexicon ([[parallel-translation-qa]]). Other checks: a gloss that is really a definition (too
long for interlinear), an empty MSA (un-parseable sense), and the **split-vs-new-entry** decision —
related readings should be senses/subsenses of one entry, not new homographs ([[homograph-number]]).

## Pitfalls

- **Gloss ≠ definition.** Stuffing a sentence into `Gloss` breaks glossing alignment.
- **Over-splitting senses** mirrors over-splitting entries; corpus evidence should justify a new sense.
- **No MSA** → the sense cannot be parsed or generated.

## Related & references

[[lexical-entry]], [[morphosyntactic-analysis]], [[part-of-speech]], [[example-sentence]],
[[semantic-domain]], [[homograph-number]], [[interlinearization]]. — FLEx Lexicon docs; LibLCM
`MasterLCModel.xml` (`LexSense`); Leipzig Glossing Rules (Comrie et al. 2008); Atkins & Rundell (2008)
on sense division. See [../References.md](../References.md).
