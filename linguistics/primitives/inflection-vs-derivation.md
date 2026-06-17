# Inflection vs derivation

> The split between affixation that fills paradigm slots without changing the word's identity
> (inflection) and affixation that makes a new lexeme, often of a new category (derivation).

**LibLCM class:** encoded in the [[morphosyntactic-analysis]] choice — `MoInflAffMsa` vs
`MoDerivAffMsa`  ·  **FLEx UI:** "Inflectional affix" vs "Derivational affix"  ·  **Tier:**
morphology/phonology  ·  **In MiniLcm:** no

## What it is (linguistics)

**Inflection** produces the grammatical variants of one lexeme: *walk / walks / walked / walking* are
all the verb *walk*, differing only in tense/agreement [[inflection-feature]]s. Inflection preserves
[[part-of-speech]] and fills a slot in a paradigm. **Derivation** creates a *new* lexeme:
*walk* → *walker* (verb → noun), *happy* → *happiness* (adj → noun), *happy* → *unhappy* (category
preserved, but a distinct lexeme worthy of its own dictionary entry). The test: would a dictionary
list it as a separate headword (derivation) or as a form of an existing one (inflection)?

The distinction is gradient cross-linguistically, but FLEx forces a clean choice because the two are
modelled — and parsed — differently.

## How LibLCM models it

The choice *is* the MSA subclass:
- **Inflectional** → `MoInflAffMsa`: the affix has one `PartOfSpeech` (input category = output
  category), realizes `InflFeats`, and fills [[affix-template-and-slot]]s.
- **Derivational** → `MoDerivAffMsa`: `FromPartOfSpeech` may differ from `ToPartOfSpeech`, and it may
  change [[inflection-class]] and stem features (`From*`/`To*` pairs).

FLEx's parser layers this as ordered operations applied in a fixed sequence — **stem formation, then
derivation, then inflection**: derivation builds the *stem* from the root (innermost), inflection wraps
the finished stem (outermost), and clitics attach outside even inflection. This is why a
[[part-of-speech]] is required morphosyntax the parser acts on at every layer (it gates which affixes
may attach and what the result's category is), not the syntax we hold out of scope. *(The doc states
the operations apply "always in the same order"; the specific "root-level / stem-level" labels are the
FLEx Conceptual Introduction's framing — exact phrasing unverified here.)*

## Hermit Crab mapping

HC realizes the layering as ordered application within a [[stratum]]: derivational affix processes
apply first (changing category/building the stem), then inflectional processes apply in their template
order. Because HC both parses and generates, an affix mislabelled inflectional-vs-derivational can
still "work" in one direction while silently producing wrong analyses in the other — exactly the kind
of fault the golden-set gate catches.

## In our change-sets

The kind field on an MSA op encodes the split:

```yaml
op: morphophonology.msa.set
entry: "-er"
msa: { kind: deriv_affix, from_pos: verb, to_pos: noun }   # derivation: changes category
rationale: "-er forms agent nouns from verbs (walk → walker); new lexeme, not a verb form."
confidence: 0.84
```

## QA & parallel relevance

The split governs glossing: inflectional affixes get grammatical glosses (PST, 3SG) in
[[interlinearization]]; derivational ones get lexical glosses. In parallel-QA, derivational gaps mean a
concept is *missing a lexeme* (lexical fix), while inflectional gaps mean a *paradigm cell* is
unrealizable (grammar fix) — different change-set targets.

## Pitfalls

- **Treating productive derivation as inflection** floods paradigms with non-words.
- **Treating idiosyncratic inflection as derivation** mints spurious entries; see [[lexical-entry]].
- **Direction-dependent silent errors** — test parse *and* generate.

## Related & references

[[morphosyntactic-analysis]], [[affix-template-and-slot]], [[part-of-speech]], [[inflection-class]],
[[inflection-feature]], [[stratum]]. — FLEx "Conceptual Introduction to Morphological Parsing";
Haspelmath & Sims (2010) ch. on the inflection/derivation cline; Maxwell (2003). See
[../References.md](../References.md).
