# golden/reference/ — external reference golden sets

Per-language gold for the four targets from **independent, authoritative** sources, plus an evaluator
that scores the induced grammar/lexicon against them — the answer to *"do the techniques actually work?"*

> **Principle (the gold is a yardstick, not a grammar-builder).** The reference gold is ONLY an
> internet-backed, Opus-assisted, cross-verified **standard for improving and assessing the parts of the
> TDD loop**. It measures the induced grammar (`cycle/` + `align/`); it MUST NOT drift into *inducing* the
> grammar itself. The cycle is never scored against its own output — always against this independent
> standard. Thin coverage (tgl/swh) is a *yardstick-coverage gap to close with more internet sources +
> Opus cross-verification*, not a reason to abandon the standard or let the cycle grade itself.

| Source | Validates | what it gives |
|---|---|---|
| **UniMorph** (lemma/form/features) | morphology, lexicon, affixes | the affix→function gold + paradigms |
| **Universal Dependencies** (FORM/LEMMA/UPOS) | POS | in-context POS from annotated text |
| **Wiktionary** via kaikki.org (word/pos/senses/forms) | **bilingual gloss**, POS, lexicon | target→English glosses (the layer UD/UniMorph lack) + more forms (lifts tgl/swh) |
| **unfoldingWord / Door43** translationWords | gloss validity | controlled English biblical key terms |

POS is a **3-way vote** (UD + UniMorph + Wiktionary) → a word ≥2 sources agree on is `verified`.

Coverage is uneven by design (Tagalog UD is a tiny test set; Swahili has no UD treebank; Tagalog has no
UniMorph) — the fetcher skips a missing source and the evaluator scores only what exists.

## Use
```bash
cd research
python golden/reference/compile.py  --pair spa   # COMBINE + CONVERT all sources → the pristine gold
python golden/reference/evaluate.py --pair spa   # score cycle/out/spa_model.json against it
python golden/reference/tests_smoke.py            # offline parser/converter tests
```
`compile.py` is the main entry; `build.py` is the lower-level fetch/parse it builds on.

## What `compile.py` produces (pristine, cross-verified, two layers)
Under `golden/_sources/reference/<pair>/` (regenerable, not committed):
- **`golden_set.json`** — the curated gold: `pos` (word→UPOS, merged from **all** UD treebanks +
  UniMorph features→UPOS, with a `verified` count where UD and UniMorph **agree** and a conflict
  sample); `affixes` (an **affix→function gold** derived by segmenting every UniMorph lemma/form pair —
  `-s`→`N;PL`, prefixes, replacive endings); `key_terms` (unfoldingWord); and `stats`.
- **`golden_lexicon.txt`** — the full real-word list (UniMorph ∪ UD): the "**more words than
  scripture**" layer (e.g. ~900k Spanish forms).
- **`golden_scripture.tsv`** — the **scripture-attested** subset (word → UPOS + source flags): the
  directly-usable validation gold. `stats.scripture_coverage` + the uncovered sample show how much of
  the NT vocabulary the references actually know (and which words none do).

Two layers by design: a broad reference (everything the sources know) **and** the scripture-attested
slice we validate parses against. Coverage is uneven (Tagalog UD tiny; no Swahili UD; no Tagalog
UniMorph) — sources are skipped gracefully and only what exists is scored.

## Destination = LibLCM / FieldWorks HC (not the online format)
The online resources speak UD **UPOS** + UniMorph **feature bundles**; the product is HC-parsable
FieldWorks data. `research/liblcm.py` converts to the destination dialect, so the gold carries both:
`pos` (source UPOS, traceable) **and** `pos_liblcm` (FLEx `PartOfSpeech`: Noun, Verb, *Subordinating
connective*, …), and each affix carries a `morph_type` + an `inflection` `FsFeatStruc`
(`-s` → `{Gender: Masculine, Number: Plural}`). That's the `LexEntry(+MoMorphType) ·
MoStemMsa/MoInflAffMsa(PartOfSpeech + FsFeatStruc) · AffixTemplate` shape the deltas apply into.

## Coverage reality (honest)
Cross-verified POS: **spa 26,698 · ind 3,953 · tgl 0 · swh 0**. Scripture coverage: **spa 0.90 · ind
0.74 · tgl 0.04 · swh 0.04**. The references are rich for Spanish/Indonesian but **thin for Tagalog
(no UniMorph, tiny UD) and Swahili (no UD, small UniMorph)** — those two need an added bilingual source
(Wiktionary via kaikki.org gives gloss + POS) to reach parity.

## What the evaluator reports
- **POS accuracy** — our `set_pos` (mapped to UPOS) vs UD on shared forms. *spa: 0.52* — honestly flags
  that the coarse gloss-derived POS is noisy (hence POS-restriction is gated in the cycle).
- **Lexicon validity** — fraction of induced roots that are real words (in UniMorph/UD). *spa: 0.60* —
  the other ~40% are over-segmentation / rare forms to clean up.
- **Gloss validity** — fraction of English glosses that are unfoldingWord biblical key terms. *spa: 75
  of 355* (abraham, amen, angel, apostle, …) — a domain-vocabulary sanity check.

These numbers are the measurement loop: change a technique, re-run, see whether POS/lexicon/gloss move.
Licenses (UniMorph CC-BY-SA, UD mostly CC-BY-SA/NC, unfoldingWord CC-BY-SA) → fetch-on-box, derived gold
only is kept.
