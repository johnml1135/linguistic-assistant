# divide-senses

> **Lump or split?** Decide whether a use is a new [[../primitives/sense]], a subsense, a separate
> entry (a [[../primitives/homograph-number]] homonym), or mere contextual variation.

**Judgment type:** decide  ·  **Grounded in:** Atkins & Rundell (2008); Kilgarriff (1997)  ·
**Used by:** [[../workflows/sense-discovery-and-disambiguation]],
[[../workflows/parallel-translation-qa]], [[../meta-workflows/build-the-lexicon]]

## The judgment

The lexicographer's perennial call. Faced with a word used two ways, the question is *one entry or
two, one sense or several?* Get it wrong and the dictionary either drowns the user in over-split
hairsplitting or hides a real distinction under a vague gloss. The trained heuristic keys on
**etymological relatedness** and **corpus behaviour**: related meanings linked by metaphor/metonymy
**lump** into one entry's ordered senses; unrelated meanings that merely share a spelling **split**
into separate [[../primitives/homograph-number]] entries.

## Heuristic / procedure

```
1. SYNCHRONICALLY RELATED MEANINGS? (do speakers feel one word, not two? — etymology informs but
   does not decide this; A&R treat distinct origin as the traditional cut, synchronic relatedness as
   what matters)
   ├─ NO  → SPLIT: separate entries, distinct homograph numbers (homonyms: bank₁ 'riverside' / bank₂ 'finance')
   └─ YES ↓
2. Are the meanings related by METAPHOR / METONYMY / regular extension?
   ├─ YES → LUMP into ONE entry; order senses primary → figurative/derived (polysemy)
   └─ NO / opaque ↓
3. Does CORPUS USAGE cluster into separable contexts (Kilgarriff)?  +  is there a frequency asymmetry?
   ├─ clusters cleanly + asymmetric frequency → SPLIT a distinct sense (or subsense if tightly nested)
   └─ overlapping / continuous usage → DO NOT split: one sense, contextual variation only
```

Atkins & Rundell's discipline: senses are *lumped first*, split only when the corpus forces it; the
homonym cut rests on synchronic unrelatedness (distinct etymology is the traditional signal, not the
sole criterion). A subsense is for a use clearly *under* a parent sense, not coordinate with it.

## Inputs → outputs

- **In:** a headword with ≥2 candidate uses — gloss variants, corpus citations, or a
  [[../workflows/parallel-translation-qa]] mismatch — plus existing senses and etymology if known.
- **Out:** a decision — *lump* (add/order a [[../primitives/sense]] or subsense on one entry), *split*
  (new entry with a [[../primitives/homograph-number]]), or *no change* (contextual variation) — with
  rationale, confidence, provenance, and the citation cluster that motivated it.

## Interaction with other skills & the gate

Receives candidates from [[propose-from-evidence]] and from translation-pair mismatches in
[[../workflows/parallel-translation-qa]]. When the data won't settle the call, it routes to
[[guess-ask-or-defer]] — a native-speaker question phrased by [[phrase-for-a-speaker]] ("could one word
do both of these jobs?") often resolves lump-vs-split fast. Splits/merges that touch parsing pass
[[read-the-gate]].

## Failure modes / guardrails

- **Over-splitting.** The dominant failure; prefer **fewer, well-evidenced senses**. Don't mint a sense
  per context — Kilgarriff's point is that senses are task-relative clusters, not natural kinds.
- **Sense boundaries are fuzzy.** Treat the cut as a judgment under the lexicon's purpose, not a fact;
  record confidence.
- **False homonymy.** Don't split etymologically related senses into homonyms just because the link
  feels distant; homonymy needs *unrelated* roots, not merely *far* ones.
- **Thin corpus.** Frequency-asymmetry and clustering signals are unreliable on small data — flag
  *(low-confidence)* and revisit as the corpus grows.

## Training basis

Atkins & Rundell (2008) on lumping/splitting and entry structure; Kilgarriff (1997), "I don't believe
in word senses," on senses as task-relative corpus clusters. See [../References.md](../References.md)
§5, §9.
