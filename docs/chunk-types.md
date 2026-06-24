# Chunk types — what the system auto-finds

The goal is a system that, handed an **unknown** language, works out *what to look at next* on its own and
presents it well. To do that it needs a fixed catalog of the kinds of thing there are to discover — the
**chunk types** — each with: how it's auto-found (the signal), what it depends on (so we never propose a
chunk before its prerequisites), and how we measure its **unexplained mass** (so the finder can rank them).
The frontier finder (`review/frontier.py`) probes each, gated by readiness, and surfaces the biggest.

A chunk type is "done" only relative to evidence; the finder reports the *largest unexplained mass among
ready chunks* as the next thing for the human (Opus, for the golden sets) to work through.

## The catalog (tiered by dependency)

### Tier 0 — Foundation (what the rest is expressed in)
1. **Orthography & segmentation** — graphemes, digraphs, casing, word/token boundaries.
   *Signal:* character + length distributions; type/token. *Depends:* —. *Impact:* % of running text not
   cleanly tokenizable. *Detector:* corpus profiling.
2. **Switches (typological frame)** — the 12 master switches (synthesis, affix polarity, infix,
   reduplication, harmony, nasal, tone, gender/noun-class, case, TAM locus, agreement, articles).
   *Signal:* per-switch detector + WALS/Grambank cross-check. *Depends:* orthography. *Impact:* # switches
   still unconfirmed (each gates a whole branch). *Detector:* `review/deferrals/profile_detect.py` (built).

### Tier 1 — Lexicon & categories
3a. **Proper nouns / names (the NER tail)** — the genealogies and place names (Matthew 1 is wall-to-wall
   names) are a *separate* tail, not language structure. *Signal:* a name gazetteer / NER (capitalization is
   gone — both corpus sides are lowercased). *Depends:* segmentation. *Impact:* % tokens that are names.
   *Detector:* NER/gazetteer (pending). *Note:* it is **shown but never the structural recommendation**;
   accounting for it stops names inflating the "unknown word" gap.
3. **Word classes (POS)** — noun / verb / adjective / … the basic categories.
   *Signal:* distributional clustering + bilingual alignment; the structural gap is **recurring** unknowns
   (hapax unknowns ≈ the name/rare tail). *Depends:* segmentation. *Impact:* % tokens that are recurring
   unknown words. *Detector:* gold reference (partial).
4. **Additive morphology (affix inventory)** — the productive concatenative prefixes/suffixes + their
   function. *Signal:* recurring word-edge substrings over shared stems; alignment for the function.
   *Depends:* segmentation, switches (affix polarity). *Impact:* % word *types* not segmentable by known
   affixes — the morphology gap (the bulk of an agglutinative language). *Detector:* `induce/*` + `align/*`
   (built).
5. **Morphotactics (slots / templates)** — the order and co-occurrence of affixes (position classes).
   *Signal:* affix adjacency + ordering statistics. *Depends:* affix inventory. *Impact:* analysed words
   that violate any learned ordering. *Detector:* planned.

### Tier 2 — Groupings (the compile root)
6. **Classes (gender / noun class / declension / conjugation)** — the partitions words inflect by.
   *Signal:* shared inflectional behaviour (article gender, class prefix, agreement footprint). *Depends:*
   word classes; switches (gender/noun-class). *Impact:* % nouns/verbs not assignable to any class.
   *Detector:* `review/classes.py` (built — human-declared schema, the compile root).
7. **Agreement / concord** — how a class/feature propagates onto surrounding words (article, adjective,
   verb). *Signal:* cross-word co-variation between a controller and its targets (Corbett). *Depends:*
   classes (declared). *Impact:* classes with empty concord + nouns classifiable *only* by the agreement
   they trigger (e.g. zero-prefix Bantu nouns). *Detector:* planned — the cross-word conditioner.

### Tier 3 — Variation & rules
8. **Allomorphy (conditioned variants)** — one morpheme, several shapes. *Signal:* same-meaning form
   families in complementary distribution. *Depends:* affix inventory. *Impact:* # families still
   *enumerated* (the enumeration debt). *Detector:* `review/allomorph.py` (built).
9. **Morphophonological rules** — the rules that derive allomorphs (vowel harmony, glide formation, nasal
   assimilation). *Signal:* the alternation + its conditioning environment. *Depends:* allomorphy,
   phonological substrate. *Impact:* allomorph families collapsible to one underlying form + a rule (MDL
   gain). *Detector:* `engine/hc_collapse.py` + `review/promote.py` (built for glides).
10. **Non-concatenative processes** — reduplication, infixation, templatic/root-and-pattern, ablaut.
    *Signal:* internal copies, non-edge alternations. *Depends:* segmentation, switches. *Impact:* words
    unparseable by pure concatenation (e.g. Tagalog reduplication). *Detector:* switches detect; emitter
    planned.

### Tier 4 — The tail
11. **Exceptions / irregulars / suppletion** — the residue, and the *layered* exception classes
    ("rule, except after c, except …"). *Signal:* a rule's own counterexamples. *Depends:* the rule it
    excepts. *Impact:* exception rate vs the productivity (Tolerance) threshold. *Detector:* the layered
    rule-block engine (designed; recursive Tolerance + ordered round-trip).
12. **Homographs / syncretism** — one form, several functions. *Signal:* high-entropy alignment that
    sharpens when conditioned on an environment. *Depends:* affix inventory / POS. *Impact:* ambiguous
    high-frequency forms. *Detector:* `review/constraints.py` (built).

## Probe status (2026-06-24, after the 5-cycle build-out)

**All 13 chunk types now have real probes (none pending):** orthography (digraph candidates) · switches ·
proper-nouns (NER tail, shown-not-recommended) · word-classes (recurring-OOV, name-aware) · additive-affixes
(known affix→known stem, incl. circumfix) · morphotactics (multi-affix peel depth) · classes (with the
agreement feedback) · agreement (associative concord + zero-prefix cracking) · allomorphy (proxy) ·
morphophonology (vocalic-alternation debt, proxy) · non-concatenative (reduplication) · exceptions
(irreducible residue) · homographs. Proxies (allomorphy, morphophonology, orthography, proper-nouns) are
shown but never drive the recommendation.

## How the finder uses this

For a given language the finder computes, per chunk type, an **unexplained fraction** (the share of corpus
mass the chunk would account for) and a **readiness** flag (are its dependencies satisfied?). It ranks the
*ready* chunks by unexplained mass and presents the top one — with its evidence and the action to take
(which detector / phase to run, suggest → define → utilize). Because the metric is corpus mass, the same
machinery yields a *different* next chunk per language, from the data — agreement for Swahili (zero-prefix
nouns), affix morphology for Indonesian, reduplication/voice for Tagalog, the inflected-form tail for
Spanish — with no per-language hand-tuning. That is the system working on an unknown language.
