# Glosses Improvement Plan — evaluation, calibration, and scaling research (GIP)

Research backing three gaps surfaced by the PolyGloss 18-language pilot (see `Polygloss_integration.md`,
`corpus/polygloss/out/PILOT_REPORT.md`): (1) `parse_rate`/`final_coverage` conflate "parsed" with
"parsed AND meaningfully labeled," hiding that essentially all 18 induced grammars have almost no real
grammatical feature labels; (2) the one affix-labeling mechanism in the main induction loop
(`induce/glossing.py::infer_affix_glosses`) has no held-out check, unlike the separate, unused
`review/affix_function.py`; (3) every pilot language got the same ~150s budget regardless of whether it
had 631 sentences (Basque) or 36,771 (Arapaho). This doc surveys the state of the art for fixing these
three gaps and recommends concrete, ranked next steps. **Research only — no code touched.**

---

## 1. State of the art

### 1.1 SIGMORPHON shared-task evaluation methodology (structure vs. label)

- **SIGMORPHON 2022 morpheme segmentation** (Batsuren et al., ACL Anthology `2022.sigmorphon-1.11`,
  arXiv:2206.07615). Subtask 1 (word-level): ~5M words across 9 languages (Czech, English, Spanish,
  Hungarian, French, Italian, Russian, Latin, Mongolian). Subtask 2 (sentence-level): 18,735 sentences,
  3 languages (Czech, English, Mongolian). Metrics: precision/recall/F1 over predicted-vs-gold morpheme
  *strings*, plus average Levenshtein edit distance. Best system averaged 97.29% F1 (93.84% on English,
  99.38% on Latin). **This task is purely structural** — morphemes are unlabeled spans, there is no
  gloss/feature dimension at all. It's the field's cleanest example of a "structure found" metric with
  zero "meaning labeled" component, i.e. exactly the `parse_rate`/`structural_coverage` half of what our
  pipeline needs, with nothing analogous to `feature_recall` mixed in.

- **SIGMORPHON 2023 interlinear glossing** (Ginn et al. baseline paper, `github.com/sigmorphon/
  2023glossingST`; Girrbach 2023 won with a hard-attention encoder-decoder that induces its own
  segmentation). This shared task's own data (SIGMORPHON-ST) is **one of the four sources**
  `Polygloss_integration.md` §1 names for PolyGloss's lineage (ODIN, IMTVault, SIGMORPHON-ST,
  Wav2Gloss) — i.e. it is a direct **ancestor** of a slice of our pilot corpus, not a separately-sourced
  but comparable task; its 9-language held-out set (Arapaho, Gitksan, …) is the same one
  `Polygloss_integration.md` §1 cites for the 400x Arapaho/Gitksan volume spread. Two tracks:
  closed (train on translations+glosses only) vs. open (also given gold segmentation at train time) —
  itself a structure-vs-label separation at the *training* level, not just scoring. Reported metrics:
  (a) **morpheme-level accuracy** (dot-separated element match) vs. **word-level accuracy** (whole
  fully-glossed-token match, e.g. `chiens → dog-PL` scored as one unit or zero), and (b) **glossing
  accuracy separately on bound morphemes ("Grams") vs. free morphemes/stems ("Stems")** — the baseline
  and winner results tables report `Stems` and `Grams` as two distinct columns per language/track. This
  is the direct, citable precedent for exactly the split gap #1 asks for: it already has an
  established name in the field (Stems vs. Grams), not something we'd be inventing.

- **The PolyGloss corpus paper itself** — "Massively Multilingual Joint Segmentation and Glossing"
  (arXiv:2601.10925, LECS Lab / CU Boulder). Its corpus-size numbers match `Polygloss_integration.md`
  §1 exactly (353,266 total examples, 2,077 languages, 340,251 train) — **this is the paper describing
  the exact corpus our pilot benchmarks against**, not a loosely related shared task. It reports
  segmentation quality via a modified F1 (citing Mager et al. 2020: precision computed over predicted
  morphemes that also occur in the gold segmentation) *separately* from glossing quality via
  **Morpheme Error Rate** (their primary gloss metric, a WER analog) plus word/character error rates,
  BLEU at morpheme/word/character granularity, and morpheme/word-level accuracy. It additionally
  proposes an **alignment score**: whether the predicted segmentation and predicted glosses stay
  mutually consistent with each other, not just each independently correct against gold — a third axis
  beyond "structure right" and "label right." Notably, its own stated limitation (§12): *"For
  morphological segmentation, we do not differentiate between surface-level morphemes and
  underlying-form morphemes"* — and it does **not** report a Stems/Grams split in its own results,
  despite that split existing in the 2023 shared task it built on. This means the Stems/Grams
  separation is a real but not fully field-converged practice — SIGMORPHON 2023 did it, the newer paper
  on the identical corpus didn't carry it forward as a headline number.

- **GlossLM** (Ginn et al. 2024, EMNLP, arXiv:2403.06399) — same LECS Lab group, direct predecessor
  corpus to PolyGloss (`lecslab/glosslm-corpus-split` on HF, same organization as
  `lecslab/polygloss-corpus`). Metrics: **morpheme accuracy** (position-sensitive — an inserted or
  deleted gloss cascades errors through every following position in that word, WER-like), **word
  accuracy** (whole gloss sequence exact match), and **chrF++** (character n-gram F1, robust to
  insertions/deletions unlike positional accuracy). It defines the *same* Leipzig all-caps-vs-lowercase
  convention `corpus/polygloss/convert.py::is_grammatical_gloss()` already implements, but — like the
  2026 paper — does not split its own reported accuracy numbers by that convention. Held-out sizes for
  its 7-language eval set (train/eval/test): Arapaho 39,132/4,892/4,892; Tsez 3,558/445/445; Uspanteko
  9,774/232/633; Gitksan 74/42/37; Lezgi 705/88/87; Natugu 791/99/99; Nyangbo 2,100/263/263 — closely
  matching (not identical to, likely a later corpus snapshot) the volumes our own pilot found for the
  same 5 overlapping languages (`PILOT_REPORT.md`: Lezgian 646 train, Nyangbo 1,221 train, Natügu 786
  train), which cross-validates that our pilot's exclusion of Gitksan (89 rows, below `Polygloss_
  integration.md` §5's 500–1,000 volume floor) tracks the same language the field itself finds hardest
  to get traction on. GlossLM's pretrained Arapaho morpheme accuracy is 85.2% (vs. 79.7% prior SOTA) —
  **not directly comparable** to our pilot's Arapaho `lemma_recall`=0.263 (`PILOT_REPORT.md`): different
  metric (positional gloss-sequence accuracy with massive cross-lingual pretraining vs. our exact-string
  match on a single slugified gloss with a THOT-aligned root, no pretraining at all), flagged here so
  the two numbers are never conflated later.

### 1.2 Calibration / confidence-gating for weak-signal induction

- **MDL-gated symbolic morphology induction** — Goldsmith, "Unsupervised Learning of the Morphology of
  a Natural Language" (*Computational Linguistics* 27(2), 2001; the Linguistica system). Heuristics
  propose restructurings of the induced grammar ("signatures" — sets of words sharing a stem+affix
  paradigm); MDL (total bits to encode grammar + corpus-given-grammar) is the sole accept/reject
  criterion for whether a proposed change survives. Corpora tested ranged 5,000–500,000 words across
  European languages. This is a **global compression criterion**, not a per-affix significance test —
  it answers "is the grammar as a whole better" rather than "is this one label trustworthy," which is a
  different question shape than gap #2 needs, but it is the most established acceptance rule for
  *symbolic* (non-neural) morphology induction specifically, and this codebase already has a partial
  analog: per `MEMORY.md`'s deferral-packages entry, `review/deferrals/` does a "ΔMDL assessment" for a
  different decision (homograph/allomorph resolution tickets) — not independently re-read in this
  research pass, flagged as a follow-up rather than verified here.
- **Bayesian nonparametric adaptor grammars** (Johnson & Goldwater, NAACL 2009, "Improving
  nonparametric Bayesian inference: experiments on unsupervised word segmentation with adaptor
  grammars"). Posterior probability over a PCFG-with-memoization gives every segmentation a natural
  confidence score via MCMC sampling. Principled, but requires an inference engine (Dirichlet-process/
  MCMC over PCFGs) that is architecturally foreign to this pipeline's deterministic-HC-verifier design
  — flagged as a poor engineering fit below, though the underlying idea (confidence is posterior mass,
  not a binary accept/reject) is portable in spirit even without adopting the machinery.
- **Corpus-linguistics association measures** — mutual information / PMI (Church & Hanks 1990), lift,
  log-likelihood ratio: the well-established family that `review/affix_function.py::rank_functions`
  (`LIFT_MIN=1.6`, `MIN_SUPPORT=6`, `MIN_SHARE=0.30`) is a specific instantiation of, though the module
  doesn't cite the family by name. Search turned up **no single published paper** that packages
  "affix→feature lift + held-out prediction accuracy" as one named method specific to morphology —
  `affix_function.py`'s combination reads as a reasonable original synthesis of two independently
  well-established techniques (association-strength filtering + held-out validation), not an
  implementation of a specific citable algorithm. Stated plainly so it isn't later cited as more
  externally-validated than it is.
- **Binomial confidence intervals on small held-out counts** — standard statistics (Wilson 1927 score
  interval; Clopper-Pearson exact interval), not morphology-specific, but directly relevant: neither
  `glossing.py::infer_affix_glosses` (no held-out check at all — gap #2) nor `affix_function.py`'s
  `heldout_accuracy = hit/seen` (lines 132-133) reports an interval around that point estimate, even
  though `seen` is frequently single-digit at the `MIN_SUPPORT=6` floor. A Wilson interval would
  visibly distinguish "4/5 accurate" (95% CI roughly 0.36–0.98) from "400/500" (95% CI roughly
  0.76–0.83) — currently both would present as a bare "0.8," collapsing exactly the distinction gap #2
  is trying to introduce.

### 1.3 Data/compute scaling for grammar induction

**This sub-area's literature is genuinely thin for symbolic/rule-based induction specifically** — flagged
per the task's request, not glossed over:

- Goldsmith's Linguistica results span corpora from 5,000 to 500,000 words across multiple European
  languages, but the published summaries available here did not yield an explicit "returns diminish at
  X words" curve — WebFetch could not extract readable text from the primary PDF/ACL-Anthology page for
  this paper in this research pass (see §4), so this is a documented gap in what could be verified
  directly, not a confirmed absence in the paper itself.
- Independent of corpus-size literature, there is a **typological complexity-measurement** literature
  that could supply the missing covariate: Bickel & Nichols' WALS "synthesis" (morphemes/word) and
  "fusion" (degree of exponence) indices, Cotterell et al. 2018 ("On the Complexity and Typology of
  Inflectional Morphological Systems," ~36 languages, showing a Pareto-style enumerative-vs-integrative
  complexity trade-off), and a 2022 NAACL paper quantifying synthesis/fusion indices and their MT impact
  — this last one's exact formulas could not be verified from the fetched PDF in this pass (§4). These
  give a principled way to say *how* morphologically complex a language is independent of how much data
  exists for it, which is the missing half of "how much data does language X need" — but no published
  work was found that combines such an index with an explicit data-requirement threshold for rule-based
  induction. The typological literature and the data-requirement question exist in parallel, not
  combined.
- The nearest indirect evidence is neural, not symbolic: the PolyGloss paper (arXiv:2601.10925) reports
  that for its 3 highest-resource eval languages (Arapaho, Uspanteko, Ainu — two of which, Arapaho and
  Ainu, are also in our own 18-language pilot) monolingual training beats multilingual cross-lingual
  transfer, while for every lower-resource language multilingual transfer wins (§7.2). This implies a
  threshold somewhere between Nyangbo-scale (2,100 examples) and Arapaho-scale (39,132 examples) past
  which a language's own data becomes self-sufficient — but the mechanism (shared subword/parameter
  transfer across languages) has no analog in a symbolic per-language grammar induced independently, so
  this transfers only as a rough intuition ("there probably is a threshold somewhere in that range"),
  not a number reusable directly.
- **Conclusion for this sub-area**: rather than import an external scaling law that doesn't exist in
  citable, symbolic-induction-specific form, the pilot's own `PILOT_REPORT.md` — 18 languages, train
  rows spanning 631 (Basque) to 36,771 (Arapaho), typology labeled per row, internal coverage and gold
  recall both reported — is already the right dataset to answer this question empirically. See §3.5.

### 1.4 Held-out validation design for morpheme→feature label assignment

- SIGMORPHON 2023's own splits (via the GlossLM table above) show the field convention is a
  sentence-disjoint dev+test split, typically a smaller fraction of train than 30% (e.g. Uspanteko
  9,774 train / 232 dev / 633 test ≈ 2%/6%; Tsez 3,558/445/445 ≈ 12.5%/12.5%). `affix_function.py`'s
  `holdout=0.3` default is markedly larger — plausibly appropriate given it's a count-based estimator
  (no gradient training to starve), not necessarily a flaw, but worth naming as a deliberate departure
  from the neural-shared-task convention rather than an unexamined default.
- **No literature was found that treats "how much held-out evidence is enough to trust a single
  morpheme→feature label" as a named framework**, distinct from generic cross-validation or
  significance testing. None of SIGMORPHON 2022/2023, GlossLM, or the PolyGloss paper report a
  per-affix confidence, significance test, or minimum-support threshold for individual gloss decisions
  — they report only aggregate corpus-level accuracy. By that comparison, `affix_function.py`'s
  per-affix support/share/lift + held-out-accuracy design is already *more granular* than anything
  found in the published shared-task literature, even though (per §1.2) it isn't itself drawn from a
  specific paper. The gap isn't that our codebase lacks a framework the field has — it's that the field
  hasn't published one at this granularity either, so any framework here would be genuinely novel
  within the morphology-induction literature, not an import.
- Practical, citable-but-generic recommendations that do transfer: k-fold cross-validation instead of a
  single train/held-out split once a corpus drops below roughly 1,000 sentences (general ML practice —
  a single split's held-out estimate has high variance at that scale), and a binomial CI (§1.2) on the
  resulting accuracy rather than a bare point estimate.

---

## 2. Applicability to this codebase

Constraints repeated from the task brief, checked against each finding above:

- **Must work in a symbolic pipeline with a deterministic HC verifier as the oracle** (no torch/GPU,
  per `research/README.md`'s architecture decision). This rules out adopting adaptor-grammar/MCMC
  posterior confidence (§1.2) as anything more than a conceptual borrow — the pipeline's whole design
  point is a deterministic `hc` CLI call, not a stochastic inference loop. It does NOT rule out MDL
  (§1.2): computing a description length over an `engine.grammar.LangModel` (roots + affixes + rules)
  is pure counting, no stochastic inference required, and fits the existing deterministic-verifier
  design better than any other calibration method surveyed.
- **Must be computable from data already present** (parse results, alignment tables, held-out gold
  where available). The SIGMORPHON Stems/Grams split (§1.1) qualifies immediately: `score_parses()`
  already has, for every parsed word, both the analysis's gloss list and (via `is_grammatical_gloss()`
  in `convert.py`, already written for the §4.2 lexical/grammatical morph split) the means to bucket
  each gloss lexical vs. grammatical — no new data collection, only new bucketing of existing booleans.
  Likewise `affix_function.py`'s held-out mechanism draws only on projected English UD features and
  `induce/tdd.py`'s existing per-verse structure — nothing it uses is unavailable to
  `induce/glossing.py::infer_affix_glosses`, which currently receives the same `freqs`/`glosses`
  arguments without a train/held-out split applied to them.
- **Corpora range 500–37,000 sentences** (per `Polygloss_integration.md` §5's floor and
  `PILOT_REPORT.md`'s actual span: Basque 631 to Arapaho 36,771). This is exactly the scale range where
  §1.4's "single held-out split has high variance below ~1,000" caveat bites hardest — 10 of the 18
  pilot languages (Vera'a 1,931; Lezgian 646; Nyangbo 1,221; Ruuli 2,098; Natügu 786; Selkup 2,555;
  N‖ng 2,124; Mauwake 2,133; Kalamang 1,873; Basque 631) sit under 3,000 train rows, five of those under
  1,000. A framework tuned only for Arapaho-scale corpora would silently fail on more than half the
  pilot's languages.
- The MDL route (§1.2) is the best-fitting calibration method structurally, but requires defining a
  description-length cost specifically for `engine.grammar.LangModel` objects (cost of a root entry,
  an affix entry, a morphotactic rule) — a real design task, not a metric readthrough. Scoping that
  cost function is nontrivial and is called out as unsolved in §4, not silently assumed solvable.
- The typological-complexity indices (synthesis/fusion, §1.3) are in principle computable from data
  already in `PILOT_REPORT.md`'s "Typology" column plus each language's induced affix count/root count
  — a rough proxy synthesis index (affixes per root, or mean morphemes per gold word from the PolyGloss
  gold itself) could be computed with no new data collection, though it would be an approximation of
  the WALS-style index, not the index itself.

---

## 3. Recommended paths to investigate

Ranked by (a) how directly they close one of the three stated gaps, (b) how much new machinery they
require given the constraints in §2.

1. **Split structural from functional coverage, following the SIGMORPHON 2023 Stems/Grams precedent
   (§1.1).** Extend `corpus/polygloss/score.py::score_parses()` with a `real_gloss_rate` alongside
   `parse_rate`: among words that DID parse, what fraction have at least one analysis where a
   grammatical-shaped gloss (reuse `corpus/polygloss/convert.py::is_grammatical_gloss()`) is something
   other than the placeholder `?`, independent of whether it matches the specific gold feature bundle.
   Separately, in `induce/tdd.py::coverage()` (currently returns only `(parse_rate, mean_ambiguity)`),
   add a model-level number — the fraction of `model.affixes` whose `.gloss` is a real grammatical tag
   rather than a bare surface form or `?` — and surface it in `pilot.py::run_pilot`'s persisted
   `induction` dict next to `final_coverage`. This is the number the 18-language pilot had to be
   manually reconstructed from `induce/out/*_model.json` by hand; making it a first-class reported
   field is the single highest-leverage, lowest-risk change here — no new statistics, only new
   bucketing of data every run already computes.

2. **The primary lever is the label VOCABULARY, not just the held-out gate — swap
   `infer_affix_glosses`'s English-inflection-diff labeling for `affix_function.py`'s projected-UD-
   feature labeling, which brings held-out validation with it.** `induce/glossing.py::en_morph_diff`
   (lines 19-36) can only ever emit one of six tags — `PL`, `PST`, `PROG`, `SUPL`, `CMPR`, `ADVZ` — since
   it pattern-matches English inflectional suffixes (`-s/-es`, `-ed/-d`, `-ing`, `-est`, `-er`, `-ly`).
   That is *exactly* the label set the 18-language pilot found ("only PL/PST/PROG/CMPR ever appear" —
   SUPL/ADVZ evidently never won a majority vote): gap #1's observation isn't incidental noise, it's the
   direct, mechanical ceiling of this function's design. A held-out check alone (my original framing
   here) can only ever *shrink* this already-impoverished 6-tag set — it improves precision on PL/PST/
   PROG/CMPR, it cannot introduce `Case`, `Person`, `Mood`, `Definite`, or any of the other 10 features
   `affix_function.py::FEATURE_KEYS` already tracks. `affix_function.py` is the right model to copy not
   *only* because of its train/held-out split (lines 109-137) — that generalizes narrowly — but because
   its label vocabulary is projected UD morphological features (language-agnostic, not bound to English
   surface inflection), and the held-out check comes bundled with that vocabulary rather than being a
   separate add-on. Concretely: replace (or run alongside, as a second labeling pass) `infer_affix_
   glosses`'s vote with `affix_function.py::induce_affix_functions`'s `rank_functions`/`cooccur`
   machinery, feeding it the same affix inventory (`_affixes(pair)` already does this via `induce.tdd.
   _load_prior_model`) and wiring its output back into `LangModel.affixes[i].gloss` instead of leaving
   it as a side, unconsumed report. This ties gap #1 (label poverty) and gap #2 (no held-out gate) into
   one fix instead of two.

3. **Add a Wilson-score confidence interval, not just a point estimate, wherever a small held-out count
   currently drives an accept/reject decision.** Applies to both the new held-out check in
   recommendation 2 and to `affix_function.py`'s existing `heldout_accuracy` (line 133) — report the
   interval alongside the point estimate so a decision resting on `seen=5` is visibly distinguishable
   from one resting on `seen=500`. Pure stdlib math (no `scipy` dependency needed for the Wilson
   formula), directly addresses §1.2's finding that neither existing mechanism currently reports
   uncertainty at all.

4. **Look at whether `review/deferrals/`'s existing ΔMDL assessment (per `MEMORY.md`'s deferral-
   packages entry) generalizes beyond its current homograph/allomorph-resolution scope to the
   affix-gloss-acceptance decision in recommendation 2.** Not evaluated in this research pass (out of
   scope — this pass only read `induce/glossing.py` and `review/affix_function.py`, not
   `review/deferrals/backlog.py`/`discover.py`), but §1.2 identifies MDL as the calibration method that
   best fits the deterministic, no-torch constraint, and if a working MDL-style cost function for
   `LangModel` objects already exists in `deferrals/`, reusing it is cheaper and more consistent than
   building a second, unrelated acceptance criterion. Flagged as a "look before building" step, not a
   recommendation to build from scratch.

5. **Answer the data-scaling question (gap #3) empirically from the pilot's own data rather than
   importing an external scaling law**, since §1.3 found the literature thin. `corpus/polygloss/out/
   *_pilot.json` (18 files, one per pilot language) already has everything needed: `manifest.
   target_word_types`/train row counts, `induction.base_coverage`/`final_coverage`, and
   `gold_benchmark.parse_rate`/`lemma_recall`/`feature_recall`, cross-tabulated against the typology
   label already recorded in `PILOT_REPORT.md`'s table. A script plotting/regressing train-row-count
   (or vocabulary size, which is what `pilot.py::_scale` already uses as its scaling covariate) against
   final coverage and gold recall, split by typology (polysynthetic vs. agglutinative vs. ergative vs.
   isolating), would answer "does this pilot's fixed ~150s/auto-scaled-roots budget actually undershoot
   or overshoot per language" with data already on disk — no new pilot run required to get a first
   answer, only new analysis of existing output.

---

## 4. Open questions / risks

- **A held-out gate on `en_morph_diff` alone will not move gap #1's core finding.** Recommendation 2
  spells this out, but it bears repeating as a risk: `en_morph_diff`'s output range is fixed at six
  English-inflection tags regardless of how its evidence is validated, so gating it more strictly can
  only shrink an already-narrow label set, not widen it. Anyone implementing "just add held-out
  validation to `infer_affix_glosses`" without also revisiting its label vocabulary will fix gap #2 in
  isolation and leave gap #1 (the more consequential finding — real grammatical labels are nearly
  absent across all 18 pilot languages) essentially untouched.
- **Gap #3's literature is thin, confirmed, not just under-searched.** No published work was found
  combining a morphological-complexity index (synthesis/fusion, enumerative/integrative complexity)
  with an explicit data-sufficiency threshold for rule-based/symbolic induction. Recommendation 5 above
  treats this as a feature, not a blocker — the codebase's own pilot data becomes the primary evidence
  source for this question rather than a stand-in for missing literature — but this should be stated
  candidly wherever this document's findings get used, not softened into "the literature suggests."
- **The Stems/Grams split (recommendation 1) is not a solved, converged practice even in the source
  field.** SIGMORPHON 2023 reported it; the newer PolyGloss corpus paper (arXiv:2601.10925, the paper
  describing the exact corpus this pilot uses) explicitly does NOT carry it forward in its own results
  and calls out (§12) that it doesn't differentiate surface-level from underlying-form morphemes
  either. Adopting the split here is defensible and precedented, but it would put this codebase ahead
  of, not merely catching up to, the field's most recent published practice on this exact corpus — a
  claim worth being precise about rather than presenting as "just matching the standard."
- **`affix_function.py`'s thresholds (`LIFT_MIN=1.6`, `MIN_SUPPORT=6`, `MIN_SHARE=0.30`) have no cited
  derivation**, and the literature search found no paper that would supply one for this exact
  affix→feature setup (§1.2). Any reuse of this pattern for `infer_affix_glosses` (recommendation 2)
  should treat these as hyperparameters to sensitivity-test against the existing golden sets
  (`golden_sets/spa/`, etc.), not as validated constants being imported from prior art.
- **MDL as a cost function for `engine.grammar.LangModel` is a real design task, not a metric
  readthrough** (§2) — what counts as "a bit" of grammar-description-length for a root entry vs. an
  affix vs. a morphotactic rule has to be defined for this specific grammar representation; Goldsmith's
  original formulation was for his own signature-based representation, not HC-style finite-state
  grammars, so the cost function doesn't transfer mechanically.
- **Several primary sources could not be independently verified in this research pass.** WebFetch
  returned undecoded/binary PDF content (rather than extractable text) for: Goldsmith 2001's original
  Computational Linguistics paper, the SIGMORPHON 2022 arXiv PDF (readable summary was obtained via a
  secondary ACL Anthology abstract page instead, which is thinner than the primary text), the 2022
  NAACL "Quantifying Synthesis and Fusion" paper, and "Robust Generalization Strategies for Morpheme
  Glossing in an Endangered Language Documentation Context" (arXiv:2311.02777, which looked directly
  relevant to §1.4 by title but its actual content was never verified — a candidate for a follow-up
  read, not cited above beyond its title/relevance judgment). Numbers and claims attributed to these
  four sources above rely on secondary search-result summaries, not confirmed primary-source quotes,
  and should be re-verified via direct PDF read (not WebFetch) before being cited in any external-facing
  document.
- **Whether a Wilson CI on tiny counts (`n`=5–20, common at `MIN_SUPPORT=6`) is actually decision-useful
  or just formalizes an uncertainty everyone already assumes** is itself untested — worth a quick
  prototype against real pilot data (e.g. rerunning `affix_function.py` on one pilot language and
  checking whether the interval ever changes an accept/reject call that the point estimate alone would
  have made differently) before treating recommendation 3 as settled.
