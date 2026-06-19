# assign-pos-and-msa

> Decide each lexeme's **part of speech** and each affix's **morphosyntactic analysis** (the category it
> attaches to, and whether it inflects or derives). POS is the backbone the rest of the grammar hangs
> on — affix templates are *per-POS*, agreement is *between* POS — so getting the category right is what
> lets the grammar stop attaching affixes to the wrong words.

**Judgment type:** decide  ·  **Grounded in:** POS as a *distributional* class (Harris 1951; Croft
2000); LibLCM `MoStemMsa` / `MoInflAffMsa` ([[../primitives/morphosyntactic-analysis]],
[[../primitives/part-of-speech]]); inflection vs derivation (Anderson 1992)  ·  **Used by:**
[[../workflows/morphological-parser-setup]], [[../workflows/lexeme-and-lexicon-building]],
[[../meta-workflows/steady-state-virtuous-cycle]]

## The judgment

A part of speech is a **distributional** class — *what can stand here, what affixes can attach* — not a
notional one ("naming words"). Two decisions:
- **Root POS.** Ideally from distribution; when bootstrapping from a bilingual gloss, the **English
  gloss's POS is a usable proxy** (a target word glossed *walk* is almost always a verb), refined as
  distribution accrues. Closed classes (det/pron/prep/conj/num) are high-confidence from a word list;
  open-class content words default to **noun** unless they're known verbs/adjectives.
- **Affix MSA.** Which POS does the affix attach to (`requiredPartOfSpeech`), and is it **inflectional**
  (category-preserving, fills a paradigm slot) or **derivational** (category-changing, builds a new
  lexeme)? The attaching POS is read from the **majority POS of the roots it co-occurs with**; an affix
  that attaches across categories stays unrestricted rather than being forced.

## Heuristic / procedure

```
1. Root POS: closed-class word? -> tag it. Else gloss head is a known verb/adj? -> verb/adj.
   Else -> noun (default). (Distribution overrides the gloss proxy once enough affix evidence exists.)
2. Affix MSA: collect the POS of every root the affix attaches to.
   - clear majority POS -> requiredPartOfSpeech = that POS;  mixed -> leave unrestricted (attaches to any).
   - output POS == input POS  -> inflection;  output POS != input  -> derivation (see
     inflection-vs-derivation). v1 treats induced affixes as inflectional (category-preserving).
3. Emit a POS-aware grammar: roots tagged, affix rules require their MSA POS (so an affix can't attach to
   the wrong category) — this CUTS over-generation.
4. GATE: keep the POS-aware grammar only if coverage holds; noisy POS that drops coverage must fall back
   to a single category ([[read-the-gate]], [[assess-grammar]]).
```

## Inputs → outputs

- **In:** roots + their glosses, the induced affixes, the corpus (for distribution).
- **Out:** a POS on each [[../primitives/lexical-entry]] (`MoStemMsa`) and an MSA on each affix
  (`MoInflAffMsa`: required POS + slot + inflection/derivation), each with rationale/confidence/
  provenance; and a gate verdict (coverage held → POS-aware grammar accepted).

## Interaction with other skills & the gate

POS is upstream of [[order-the-morphotactics]] (slots are position classes *within a POS*) and of
agreement checks in [[../workflows/parallel-translation-qa]]; bounded by [[assess-grammar]] +
[[read-the-gate]] (POS-restriction is accepted only if it doesn't cost coverage). Complements
[[generalize-not-enumerate]] (shape) and [[triangulate-phonology]] (sound) — category is the third axis.

## Failure modes / guardrails

- **Gloss-POS ≠ target-POS.** The English gloss is a proxy; a target word can be a different category
  than its translation — distribution wins where it disagrees.
- **Over-restriction.** Forcing an affix onto one POS when it really attaches to several blocks valid
  parses — leave genuinely cross-category affixes unrestricted; gate on coverage.
- **Default-noun bias.** Unknown content words all become nouns; revisit with distribution.
- **Inflection/derivation confusion.** A category-changing affix mislabeled inflectional corrupts the
  paradigm; check whether the output POS differs.

## From practice (the TDD cycle)

`research/cycle/pos.py:pos_of` tags roots from the English gloss (closed-class sets + common-verb/adj
lists, default noun); `assign_slots` reads each affix's **MSA** in the same pass that learns its slot —
`req_pos` = a clear-majority attached-root POS, else unrestricted. The cycle then picks the best grammar
among {unordered, ordered template, ordered+POS-aware} by lowest ambiguity with coverage held, so the
POS-aware grammar is adopted only when it earns it.

## Training basis

Distributional POS (Harris 1951; Croft 2000 *Radical Construction Grammar*); morphosyntactic analysis in
LibLCM (`MoStemMsa`/`MoInflAffMsa`); inflection vs derivation (Anderson 1992; Stump 2001). See
[../References.md](../References.md) §2 (morphology), §8 (typology), §1 (LibLCM).
