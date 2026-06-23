# Phonology architecture — consolidation proposal (2026-06-23)

Three+ phonology tools grew separately and overlap. This proposes merging them into **one
morphophonology pipeline with two evidence streams** (text-only now; audio deferred), grounded in the
linguistic theory and in how Hermit Crab actually works.

## 1. What we have (the fragments)

| role | module(s) today | does |
|---|---|---|
| **substrate** | `gold/phonology_gold.py` (`phon_feats`, `vowel_inventory`, `phonology_records`) | segment inventory + distinctive features + natural classes (the feature system HC needs) |
| **detect** | `gold/phonology_induce.py` (`nasal_assimilation`, `vowel_harmony`) | find conditioned alternations from corpus **distribution** |
| **infer UR** | `induce/phonology.py` (`propose_archiphoneme`, `collapse_families`, `enumeration_debt`) | collapse an allomorph family → one **archiphoneme** + conditioning |
| **build + verify** | `induce/hc_phonology.py` (`build_harmony_grammar`, `collapse_round_trips`) + `gold/phonology_gold.alpha_harmony_rule` + `engine/hc.build_grammar_xml(phon_rules=…)` | emit the HC `<PhonologicalRule>` and **round-trip** it |
| **promote** | `review/promote.py` + `gold/phonology_gold.active_phon_rules` | classify candidates → activate (active rule → the parse applies it) |
| **ground (audio)** | `addons/audio/features.py` (`map_phones_to_features`, `confirm_conditioning`, `triangulate_family`) | confirm the conditioning from **phone** evidence (deferred) |

**The overlap to remove:** *two* detectors (distribution in `phonology_induce`; family-finding inside
`induce/phonology`), *two* rule-XML builders (`hc_phonology.build_harmony_grammar` and
`phonology_gold.alpha_harmony_rule`), and the pieces are scattered across `gold/`+`induce/`+`review/`+
`addons/`. They are fragments of **one** pipeline.

## 2. The linguistic spine (what the theory says it must be)

- **Hermit Crab is classical SPE generative phonology** ([Chomsky & Halle 1968]; the FLEx HC parser uses
  *ordered* rules + *strata* à la Lexical Phonology, feature bundles, insert/copy — **not** autosegmental
  spreading) ([HC parser docs](https://downloads.languagetechnology.org/fieldworks/Documentation/en/User_Interface/Menus/Parser/Parsing_words_(HermitCrab).htm), [ordered-rules parsing](https://arxiv.org/pdf/cmp-lg/9411015)). **Consequence: our rules must carry an ORDER and a STRATUM (feeding/bleeding), not be a flat set.**
- **Morphophonology = a UR passed through rules to a surface form**; the abstract unit that collapses a
  neutralised alternation is the **archiphoneme / morphophoneme** ([Morphophonology](https://en.wikipedia.org/wiki/Morphophonology)). This is exactly `propose_archiphoneme`'s job (meN, -lI).
- **The discovery criterion is phonemic analysis by COMPLEMENTARY DISTRIBUTION** — two shapes in
  non-overlapping environments are allophones of one underlying unit ([phonemic analysis](https://ecampusontario.pressbooks.pub/essentialsoflinguistics2/chapter/4-5-phonemic-analysis/)). Both our detectors are doing this (orthographically).
- **Audio uses the *same* criterion at the phonetic level**: Allosaurus maps universal *phones* →
  language *phonemes* through an **allophone layer**, allophones identified by complementary distribution
  ([Allosaurus, Li et al. 2020](https://arxiv.org/pdf/2002.11800)). So audio is a *second evidence stream
  into the same analysis*, not a separate pipeline.

## 3. The unified pipeline (one layer, two evidence streams)

```
              ┌──────────────── evidence streams ────────────────┐
 TEXT (now):  orthographic distribution of morpheme variants
 AUDIO (def): Allosaurus phones → features → allophone distribution
              └───────────────────────┬───────────────────────────┘
                                       ▼
 [1 substrate] segments + distinctive features + natural classes      (gold/phonology_gold)
        │
 [2 detect]   conditioned alternation by COMPLEMENTARY DISTRIBUTION    ← both streams feed here
        │       (one detector: distribution → candidate family)
 [3 infer UR] collapse family → 1 archiphoneme + conditioning          (induce/phonology)
        │       (neutralised feature underspecified in the UR)
 [4 rule]     emit an ORDERED HC <PhonologicalRule> in a STRATUM       (one kind→XML builder)
        │       per kind: harmony (α-feature), assimilation (place), …
 [5 verify]   HC round-trip: UR + ordered rules regenerate the         (engine/hc + induce/hc_phonology)
        │       attested surfaces, no regression  (generate direction)
 [6 promote]  classify → activate → active_phon_rules → the parse       (review/promote)
                APPLIES it  (enumeration → derived rule)
```

- **Text-only path (primary, complete on its own):** steps 1–6 run entirely from orthographic
  distribution. Every step — detect, infer-UR, verify, promote — reaches a decision with **zero audio**.
  This is the whole loop, and it is the *only* path on the critical chain.

> **INVARIANT — audio is ALWAYS optional.** No step may *require* audio, *wait* on audio, or change its
> default behaviour based on audio's presence. Audio can only ever **add** to a decision the text path has
> already made (raise a confidence, break a tie, confirm a conditioning) — never gate, block, or be a
> prerequisite. The default everywhere is *no audio*; with audio absent, the pipeline behaves identically
> except that audio-sourced confidence is simply not added. (This matches the repo-wide rule: audio is
> review-only evidence, not parser input.)

- **Deferred audio path (pure addition):** when audio happens to exist, the addon produces phone-feature
  evidence (Allosaurus → `map_phones_to_features`) that *optionally* corroborates **step 2** (does the
  alternation show up phonetically?) and **step 5/6** as a *third witness* (`triangulate_family`,
  `confirm_conditioning`) — raising confidence or breaking a tie the orthography can't. The **3-witness
  triangulation** (text distribution + HC round-trip + audio phones) is the *best case*; **2 of the 3
  (both text-side) is always sufficient** to promote. Audio's contribution is monotonic: it can move a
  candidate up, never down or off.

## 4. The gaps the consolidation must close

1. **Rule ordering + strata (the biggest one).** HC is SPE ordered-rule phonology; our rules are a flat,
   unordered set. The unified layer must assign each promoted rule a **stratum + order** and check
   feeding/bleeding interactions in the round-trip. _(New: an ordering/stratum field + an
   interaction check in verify.)_
2. **One detector** — merge `phonology_induce` (distributional) with the family-finder in
   `induce/phonology`; one `detect()` returning candidate families with their conditioning evidence.
3. **One UR→rule builder** — merge `hc_phonology.build_harmony_grammar` + `phonology_gold.alpha_harmony_rule`
   into one `rules.py` keyed by rule **kind** (harmony=α-feature; **assimilation=place** — the missing
   emitter that blocks the 5 nasal candidates from `review.promote`; …).
4. **One verify gate** — the HC round-trip (`collapse_round_trips`) is the single accept criterion; align
   `promote.verify` to call it (not just the evidence score).

## 5. Where it fits the overall flow

Phonology is the **morphophonology layer between segmentation and HC emission**:

```
corpus → segment (morphemes) → PHONOLOGY (substrate→detect→UR→ordered rule→verify) → engine/hc grammar
                                      │  promote/defer → review (tickets) → deltas → gold
                                      └← audio phone-evidence (addons/audio, deferred, as a data artifact)
```

- **Consumes:** the segmenter's allomorph families + the gold lexicon/affixes.
- **Produces:** the gold's `phonology*.jsonl` (substrate + UR + ordered rules) and the *active* rules that
  `active_phon_rules` emits so `engine/hc` **applies** them — turning enumerated allomorphs into derived
  rules (paying down the spa-4194-allomorph debt).
- **Routes** through `review/promote` (first-class: promote / defer-to-ticket / reject), honouring the
  gold-as-yardstick + deltas write-path rules.
- **Audio is an `addons/` evidence stream**, contract-clean: it *writes* phone-feature evidence as data
  that `induce`'s detect/verify *read* (no import into the optional addon; audio stays not-first-class).

## 6. Proposed module layout (the merge)

Respecting the role-based dependency contract:

```
induce/phonology/                  (the induction-side pipeline — was 3 modules)
   detect.py   ← gold/phonology_induce + the family-finder from induce/phonology   (step 2)
   ur.py       ← induce/phonology  (archiphoneme/collapse, enumeration_debt)         (step 3)
   rules.py    ← hc_phonology.build_* + phonology_gold.alpha_harmony_rule + place    (step 4, kind→XML, +order/stratum)
   verify.py   ← hc_phonology.collapse_round_trips                                   (step 5)
gold/phonology_gold.py             (substrate + records + active_phon_rules emission) (steps 1, 6-emit)
review/promote.py                  (classify + activate)                              (step 6)
addons/audio/                      (phone-evidence producer; data artifact → step 2/5)
```

## 7. Consolidation tasks

- [ ] Create `induce/phonology/` (detect · ur · rules · verify); move + de-duplicate the two detectors and
      two rule-builders into it; keep public entry points stable (`active_phon_rules`, `promote`).
- [ ] Add **rule ordering + stratum** to the rule representation + a feeding/bleeding check in `verify`.
- [ ] Build the **place-assimilation emitter** (`rules.py`, kind=assimilation) — unblocks the 5 nasal
      candidates `review.promote` already classified (ind meN-, spa coN-/iN-, tgl paN-).
- [ ] Wire `promote.verify` to the real HC round-trip (`verify.py`), not the evidence-score proxy.
- [ ] Define the **audio phone-evidence artifact** (Allosaurus → features → per-family allophone
      distribution) that `detect`/`verify` read; **additive-only** per the invariant.
- [ ] **Guard test for the invariant:** the pipeline yields *identical* promote/defer/reject decisions
      with the audio artifact absent vs present-but-stripped — audio may only raise a confidence score,
      never flip a classification or be required. (Locks "audio is always optional" into CI.)
- [ ] One phonology smoke suite spanning substrate → detect → UR → rule → verify → promote (text-only),
      with the audio path gated.

## References
[Chomsky & Halle 1968 SPE] · [HC parser (SIL)](https://downloads.languagetechnology.org/fieldworks/Documentation/en/User_Interface/Menus/Parser/Parsing_words_(HermitCrab).htm) · [Parsing with linearly-ordered phonological rules](https://arxiv.org/pdf/cmp-lg/9411015) · [Morphophonology](https://en.wikipedia.org/wiki/Morphophonology) · [Phonemic analysis](https://ecampusontario.pressbooks.pub/essentialsoflinguistics2/chapter/4-5-phonemic-analysis/) · [Allosaurus multilingual allophone system (Li et al. 2020)](https://arxiv.org/pdf/2002.11800)
