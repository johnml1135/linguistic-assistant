# Semantic domain

> A node in a universal ~1,800-item meaning taxonomy (Moe / Louw-Nida) that a sense is tagged with —
> the backbone of Rapid Word Collection.

**LibLCM class:** `CmSemanticDomain`  ·  **FLEx UI:** "Semantic Domains" (Lists area; on each sense)  ·  **Tier:** lexical  ·  **In MiniLcm:** yes

## What it is (linguistics)

A semantic domain groups words by shared area of meaning: *2.1 Body*, *7.2 Move*, *1.1.3 Weather*.
The standard hierarchy is **Ron Moe's Semantic Domains** (~1,800 domains, decimal-coded and roughly
aligned to Louw & Nida's New Testament semantic classification). Tagging each [[sense]] with a domain
turns a flat word list into a thesaurus and powers **Rapid Word Collection (RWC)** — eliciting
vocabulary domain by domain rather than word by word, which finds gaps a translation-driven approach
misses.

## How LibLCM models it

`CmSemanticDomain` is a `CmPossibility` arranged as a **tree** (decimal codes mirror depth). From
`CmPossibility` it inherits **`Name`**, **`Abbreviation`** (the decimal code, e.g. "2.7.1"), and
**`Description`**. Own properties:
- **`Questions`** — owning sequence of `CmDomainQ`, the elicitation questions. Each `CmDomainQ` has
  `Question`, `ExampleWords`, and `ExampleSentences` (all multilingual) — the prompts a fieldworker
  reads aloud, plus sample words/sentences.
- **`RelatedDomains`** — reference collection to other `CmSemanticDomain`s (cross-references; currently
  unidirectional).
- **`LouwNidaCodes`** and **`OcmCodes`** — `Unicode` strings (semicolon-delimited) linking to Louw &
  Nida and Outline of Cultural Materials codes; `OcmRefs` references `CmAnthroItem`.

The list is referenced from **`LexSense.SemanticDomains`** (a reference collection — a sense may sit in
several domains).

## Hermit Crab mapping

None. Semantic domains are meaning metadata; Hermit Crab is form/morphosyntax only and ignores them.
They matter to the AI skills layer (sense discovery, gap-finding), not to the parser.

## In our change-sets

Tagging a sense is a `lexical/*` op:

```yaml
op: lexical.sense.add_domain
sense: "kufamba#1"
semantic_domains: ["7.2.1.1"]   # Manner of movement → walk
rationale: "Gloss 'walk' matches domain 7.2.1.1 example words; aids RWC gap analysis."
confidence: 0.82
```

We reference domains by their decimal `Abbreviation` (stable) rather than GUID where possible. Ops
carry rationale/confidence/impact/provenance.

## QA & parallel relevance

Domains drive **coverage QA**: which domains have no entries (likely gaps), which senses are untagged.
The `CmDomainQ` example words are useful priors for suggesting a domain from a gloss. In a
parallel/Scripture workflow, key-term sets often cluster by domain, so domain tagging complements
[[parallel-translation-qa]] and key-term consistency. See the workflow [[semantic-domain-elicitation-rwc]].

## Pitfalls

- **Abbreviation is the code, not a short name** — don't treat "2.7.1" as a label-of-convenience.
- **Over-tagging** every sense into many domains dilutes coverage signals; tag the genuine domains.
- **`RelatedDomains` is one-directional** — don't assume a reciprocal link exists.
- **Louw-Nida / OCM codes are partial** in shipped data (royalty constraints); absence ≠ error.

## Related & references

[[sense]], [[lexical-entry]], [[semantic-domain-elicitation-rwc]], [[lexical-relation]]. — FLEx Lists
docs; LibLCM `MasterLCModel.xml` (`CmSemanticDomain`, `CmDomainQ`); Moe (2001+) RWC methodology / The
Combine / WeSay; Louw & Nida (1988) *Greek-English Lexicon of the New Testament Based on Semantic
Domains*. See [../References.md](../References.md).
