# Glosses Improvement Plan — Alignment Robustness (GIP)

Researches the state of the art for **detecting** word-alignment failure without gold data, and for
**rescuing** alignment on very small/noisy corpora, prompted by a concrete failure: on the 18-language
PolyGloss pilot (`corpus/polygloss/out/PILOT_REPORT.md`, see `Polygloss_integration.md` §6 step 3),
Nyangbo (Tutrugbu, Niger-Congo/Kwa, Ghana-Togo Mountain, 1221 training sentences) produced a THOT
gloss for only 1 of 435 induced roots (`glossed_frac=0.002`), versus 0.55–0.92 for every other one of
the 18 languages. Nothing in `align/aligner.py` or `induce/tdd.py::load_glosses` detects this — the
pipeline silently emits an unlabeled grammar. This doc is research only; no code was written or
changed.

---

## 1. State of the art

### 1.1 Word-alignment quality estimation without gold data

There is **no single canonical gold-free metric** the way AER (Alignment Error Rate, Och & Ney 2003)
is canonical for gold-based evaluation. Fraser & Marcu, "Measuring Word Alignment Quality for
Statistical Machine Translation" (*Computational Linguistics* 33(3), 2007,
https://alexfraser.github.io/pubs/fraser_tr616_alignqual.pdf) is the standard reference on this exact
gap: they show AER itself correlates poorly with downstream translation quality and propose
alternative measures — but all of theirs still assume *some* gold alignment exists for calibration,
which this project doesn't have for any of its 18+ language pairs. In practice the literature falls
back to three families of gold-free proxies:

- **Bidirectional agreement rate.** Liang, Taskar & Klein, "Alignment by Agreement" (NAACL 2006,
  https://cs.stanford.edu/~pliang/papers/alignment-naacl2006.pdf) jointly train forward (src→tgt) and
  reverse (tgt→src) directional models to maximize agreement, reporting a 32% AER reduction versus the
  standard practice of intersecting two *independently*-trained models, and their HMM pair alone gives
  a 29% reduction over symmetrized IBM Model 4. The agreement *rate itself* — the fraction of links on
  which the two unidirectional Viterbi alignments agree, before any symmetrization heuristic
  (intersection/union/grow-diag) is applied — is a widely reused per-sentence, gold-free confidence
  signal: low agreement between directions means the model is uncertain, independent of any reference.
- **Posterior confidence / entropy.** Huang, "Confidence Measure for Word Alignment" (ACL/IJCNLP 2009,
  https://www.researchgate.net/publication/220874188_Confidence_Measure_for_Word_Alignment) defines a
  per-link confidence as the geometric mean of the bidirectional alignment posterior probabilities
  (not just the Viterbi best link); low-confidence links can be filtered from phrase-extraction or
  flagged for review. The general shape — entropy or peakedness of the model's own posterior
  distribution over candidate alignments for a word — recurs across the alignment/QE literature (e.g.
  "Average Normalized Entropy" as a task-agnostic confidence metric for sequence-to-sequence
  alignment-like outputs, per search results on low-resource word-discovery work, arXiv:1907.00184 —
  full text not retrievable, cited at the abstract-claim level only).
- **Corpus-level sentence/model scores as noise filters.** Moore, "On Log-Likelihood-Ratios and the
  Significance of Rare Events" (EMNLP 2004,
  https://www.microsoft.com/en-us/research/wp-content/uploads/2004/07/rare-events-final-rev.pdf) and
  his earlier sentence-aligner (2002) use a log-likelihood-ratio (LLR/G²) statistic, not raw
  co-occurrence counts, specifically because raw counts (like Dice) overweight coincidental pairings
  under sparse data — directly relevant to §1.4 below. Downstream, tools in the OpusFilter/Bicleaner
  family use a *sentence-level* alignment/cross-entropy score to discard corpus noise before training —
  a coarser, corpus-scale version of the same "the model's own score says this pair is suspicious" idea.

**This repo already independently invented an instance of proxy #3.** `align/eflomal_vs_hmm.md`'s
"THOT ∩ HC accept rate" (does THOT's alignment agree with HC's independently-parsed segmentation) and
the PolyGloss pilot's ad hoc `glossed_frac` statistic (fraction of induced roots that got *any*
confident THOT gloss) are both gold-free, model's-own-output diagnostics — they just aren't
automatically computed or gated on inside the core pipeline yet (see §3.1).

### 1.2 Eflomal specifically, and its known failure modes

Eflomal (Östling & Tiedemann, "Efficient Word Alignment with Markov Chain Monte Carlo," *Prague
Bulletin of Mathematical Linguistics* 106, 2016, pp. 125–146, DOI 10.1515/pralin-2016-0013; built on
the earlier `efmaral`, https://github.com/robertostling/efmaral) is a Bayesian HMM-with-fertility
model: **Dirichlet-prior-smoothed** lexical, jump, and fertility distributions, inferred by Gibbs/MCMC
sampling rather than EM point estimates. Its own README
(https://github.com/robertostling/eflomal/blob/master/README.md) reports, at WMT scale (1.13M
sentence-pair en-fr): eflomal AER 0.081 in 337s vs. fast_align AER 0.153 in 241s, and near-`efmaral`
parity (0.081 vs 0.085). **No GIZA++ comparison is published in that README**, and no minimum
corpus-size or vocabulary-size threshold is documented anywhere in the tool's own materials — the
Bayesian/Dirichlet-smoothing design is *motivated* by sparse-data robustness (that's the standard
rationale for priors over raw EM), but this is a design-intent claim, not a measured floor.

**A directly relevant, underused feature**: eflomal ships `eflomal-makepriors` / `--priors`, an
explicit small-corpus workflow — align a large corpus, extract Dirichlet priors from it via
`eflomal-makepriors`, then align a *small* corpus supplying those priors instead of flat/uninformative
ones. The README states this is "much faster than merging...and aligning them jointly, while nearly as
accurate." This is eflomal's own acknowledgment that a small corpus alone under-informs its priors —
and it's not exercised anywhere in `align/backends.py::eflomal_align()`, which calls
`word_align_corpus(aligner="eflomal", ...)` with no priors argument (see §2, §3.4 for the caveat that
this may not even be exposed through the `sil-machine`/THOT Python wrapper this repo uses).

**No direct, controlled eflomal-vs-fast_align-vs-GIZA++ comparison specifically in the
hundreds-to-low-thousands-sentence-pairs regime was found** despite targeted searching — every
comparison located (including this repo's own `align/eflomal_vs_hmm.md`, which compares eflomal only
against THOT's own HMM backend, on 400-verse samples) is either WMT-scale or an internal
same-toolkit comparison. This is a real, flagged gap in the literature, not a claim this doc can
verify — see §4.

Neural aligners — **awesome-align** (supervised, fine-tuned mBERT/XLM-R on parallel text) and
**SimAlign** (unsupervised, contextualized-embedding similarity, arXiv:2004.08728) — require
torch + a pretrained multilingual transformer, a hard violation of this repo's no-torch/GPU-in-core-loop
constraint (`research/README.md`). Noted for completeness only: search results (a Romansh/German
zero-shot study) put both at AER ≈0.22, beating fast_align in that setting, and a low-resource-transfer
survey claims embedding-based alignment quality "is not affected by the amount of parallel data" the
way count-based aligners are — but **this is doubly moot for Nyangbo/Tutrugbu specifically**: it is a
Ghana-Togo Mountain Kwa language with no ISO presence in mBERT's ~104 or XLM-R's ~100 pretraining
languages, so its subword embeddings would almost certainly be untrained noise even if torch were
permitted.

### 1.3 Self-training / bootstrapping / co-training for the cold-start case

Classic agreement-based joint training (Liang et al. 2006, §1.1) is not designed for cold start — it
assumes each unidirectional model already has *some* signal to agree on. Most alignment self-training
literature is the same shape: it **improves an aligner that is already producing something usable**
(e.g., adds pseudo-labeled pairs, retrains, repeats) — this repo's own `induce/cotrain.py` is exactly
this family: HC's coverage gap tells THOT what to re-align over, THOT's confident (`prob >= GATE=0.5`,
`GATE` defined at `induce/cotrain.py:34`) content-word links propose new roots, gated by a coverage-must-rise
guard. **`cotrain.py` has no fixpoint escape for the case where cycle 1 itself proposes nothing** —
`propose_roots()` (`induce/cotrain.py:54-82`) requires `table.best(w).prob >= gate`; if THOT's very
first alignment pass over the corpus never produces a confident link anywhere (exactly Nyangbo's
observed `glossed_frac=0.002`), the loop prints "no confident proposals — fixpoint" on cycle 1 and
exits with zero gain — the loop amplifies an already-working aligner, it cannot bootstrap one that
never started.

Three lines of literature come closer to true cold-start rescue, none of them a single canonical
citation the way AER is for evaluation:

- **Bilingual-lexicon/cognate seeding.** Search results on "Bootstrapping Unsupervised Bilingual
  Lexicon Induction" report reliable projections bootstrapped from seed dictionaries as small as
  50–100 word pairs, with identical-string and cognate matching a standard low-cost seed source for
  *related*-language pairs. This does not help English↔Nyangbo (unrelated families, no expected
  cognates) but is a real option for other thin languages in the 18-language batch that share a family
  with a better-resourced neighbor (worth checking case by case, not assumed generally).
- **Pivot/triangulation through a third language.** Well-studied for phrase-based MT (Dholakia 2014,
  https://aclanthology.org/2014.amta-researchers.24.pdf; Wu & Wang's earlier pivot-language work) —
  align source↔pivot and pivot↔target separately, compose. Blocked in practice here: it requires a
  *second* parallel corpus (pivot↔Nyangbo, or English↔some-Kwa-relative) that does not obviously exist
  for most PolyGloss pilot languages — a data-availability blocker, not an engineering one.
  and pivot-target parallel corpora, then compose.
- **Subword sampling.** "Subword Sampling for Low Resource Word Alignment" (arXiv:2012.11657) —
  a Bayesian-optimization search over subword granularities feeding *into* fast_align/eflomal (not a
  replacement for them), tested on en-de/fr/ro/fa/hi/iu. Its headline claim: 5K parallel sentences +
  subword sampling matches conventional word-level alignment trained on 100K sentences, and the method
  "consistently outperform[s] word-level alignment" on all six pairs tested, baselined directly against
  fast_align/eflomal. This is the single most directly actionable piece of literature found for §1.3:
  non-neural, explicitly targets the low-resource regime, and composes with the existing THOT backend
  rather than replacing it. Caveat: the smallest corpus size tested (5K sentences) is still ~4x larger
  than Nyangbo's 1221 — whether the method degrades gracefully further down, or needs a data floor of
  its own, is unverified by this search.

No standard, named "cold-start fallback strategy" specific to word alignment was found as a single
citation. The practical synthesis: fall back to a lower-variance, fewer-free-parameters objective
(association-score co-occurrence, not full HMM/fertility) when the corpus can't support the richer
model's parameter count, and/or seed with whatever cheap bilingual signal exists (cognates, shared
proper nouns/names, loanwords) before trusting the statistical aligner's own EM/MCMC estimate.

### 1.4 Small-corpus alignment alternatives to IBM/HMM-family aligners

This repo's own `align/cooccur.py` is a **raw Dice-coefficient**, greedy-independent-argmax aligner:
for each target token, picks the source token maximizing `Dice(s,t) = 2·cooc(s,t)/(count(s)+count(t))`,
with no smoothing and no constraint that two target tokens can't independently pick the same source
token. Two concrete upgrades exist in the literature at the same non-neural, dependency-free altitude:

- **Melamed's competitive-linking algorithm** ("A Word-to-Word Model of Translational Equivalence,"
  ACL 1997/2000, https://arxiv.org/pdf/cmp-lg/9706026): score every source-target type pair with a
  **log-likelihood-ratio (LLR/G²) association statistic** (Dunning 1993, as also used in Moore's
  rare-events paper, §1.1) rather than Dice, then perform **one-to-one competitive assignment**
  globally — greedily link the single highest-scoring pair, remove both words from further
  competition, repeat, instead of letting every target token pick independently. LLR is specifically
  designed to discount low-count coincidental co-occurrences (Dice does not — it's a ratio of raw
  counts, and with a 1221-sentence corpus most word-pair co-occurrence counts are 1 or 2, exactly where
  Dice is least trustworthy and LLR's significance correction matters most).
- **Phonologically-informed edit-distance alignment** ("Phonologically Informed Edit Distance
  Algorithms for Word Alignment with Low-Resource Languages," SCiL,
  https://openpublishing.library.umass.edu/scil/article/id/1076/ — full text blocked by a bot-wall
  during this research, so only the abstract-level claim is verified here): uses edit-distance
  neighbors of a word in a *high-resource pivot* to inform alignment, with substitution penalties
  weighted by phonological/distributional similarity rather than raw Levenshtein distance; reported to
  outperform a plain-Levenshtein baseline. Not independently verified beyond the abstract in this
  research pass.

Neither is torch/GPU-dependent; both are drop-in-shaped relative to `cooccur.py`'s current interface
(`cooccur_align(rows) -> list[Alignment]`).

---

## 2. Applicability to this codebase

| Candidate | No-torch fit | Fits 500–2000-sentence corpora | Integration shape |
|---|---|---|---|
| Gold-free confidence diagnostic (glossed_frac / best-prob distribution) | Yes — pure arithmetic over `GlossTable` | Yes, in fact this is the exact regime it needs to catch | Natural fit: `align/aligner.py::align()` already returns `(GlossTable, backend_used)`; a third value or an attached stat is a small, additive change |
| Bidirectional agreement rate | Yes | Yes | **Unverified**: needs checking whether `machine.py`'s `word_align_corpus(..., symmetrization_heuristic=...)` exposes the pre-symmetrization forward/reverse alignments, or only the already-merged result (`align/backends.py:32-35` only reads `row.aligned_word_pairs` post-symmetrization) |
| eflomal `--priors` primed from a related/larger corpus | Yes (still THOT/eflomal, no new deps) | Directly targets this regime | **Unverified**: `align/backends.py::eflomal_align()` calls `sil-machine`'s `word_align_corpus()` wrapper, not the native `eflomal`/`eflomal-makepriors` CLI, and the docstring (`backends.py:1-8`) is explicit that this project deliberately uses THOT's native C++ `EFLOMAL` model type, not the standalone `eflomal` PyPI package whose README documents `--priors` — whether THOT's port carries the same priors mechanism is unknown without reading `sil-thot`'s own source/docs |
| Melamed LLR + competitive linking | Yes — dependency-free, same profile as `cooccur.py` | Yes | Direct, same-shaped rewrite of `align/cooccur.py::cooccur_align()`; could also become a smarter "auto" fallback branch in `align/aligner.py::_run()` |
| Subword sampling | Yes (feeds fast_align/eflomal, no torch) | Marginal — smallest tested corpus (5K) is ~4x Nyangbo's size; ungraceful degradation below that is unverified | Would sit as a pre-processing stage before `align/backends.py::eflomal_align()`, independent of `induce/`'s own morpheme-boundary goals — but conceptually in tension with them (subwords ≠ morphemes) unless scoped as alignment-only, discarded after |
| Cognate/bilingual-lexicon seeding | Yes | Yes | No integration point exists yet; would need a new seed-dictionary input to `align/aligner.py::align()`, and doesn't help English↔Nyangbo specifically (unrelated families) |
| Pivot/triangulation | Yes, in principle | N/A — blocked upstream | Blocked: no known third parallel corpus (pivot↔Nyangbo) exists to actually build this on |
| Neural aligners (awesome-align/SimAlign) | **No** — hard constraint violation | Reported strong even at small scale, but moot here | Out of scope; also likely non-functional for Nyangbo specifically (absent from mBERT/XLM-R pretraining) |

---

## 3. Recommended paths to investigate (ranked)

1. **[Highest priority, cheapest, do first]** Add a gold-free alignment-confidence diagnostic to
   `align/aligner.py::align()`. Concretely: compute, over the returned `GlossTable`, the fraction of
   target word types whose `table.best(w).prob >= GATE` (reuse `induce/cotrain.py`'s `GATE = 0.5` for
   consistency with the existing "confident" threshold used elsewhere in the pipeline), and/or the
   median `best().prob` across all target types. This is exactly the ad hoc `glossed_frac` statistic
   that already caught Nyangbo in `corpus/polygloss/out/PILOT_REPORT.md` — promoting it into
   `align/aligner.py`'s return value (or a small new `align/diagnostics.py`) makes every future
   language self-report instead of relying on someone reading a report table. Gate
   `induce/tdd.py::load_glosses` and/or `induce/cotrain.py::cotrain()`'s use of the alignment table on
   this diagnostic — e.g., warn (not silently proceed) below some threshold. The threshold itself needs
   real calibration (see §4) before it should hard-fail anything.
2. **[Medium priority, needs a spike before committing]** Investigate whether `machine.py`'s
   `word_align_corpus()` (used in `align/backends.py::eflomal_align()`) exposes the pre-symmetrization
   forward/reverse Viterbi alignments, or only the merged `GROW_DIAG_FINAL_AND` result. If it does,
   the bidirectional agreement rate is a second, independent, cheap confidence signal, cross-checkable
   against diagnostic #1 (do they agree that Nyangbo is bad, or does one flag it and not the other —
   that itself would be informative about *why* it's failing).
3. **[Medium priority]** Rewrite `align/cooccur.py::cooccur_align()` from raw Dice + independent argmax
   to Melamed-style LLR association + one-to-one competitive linking. Same dependency-free profile,
   directly improves the path that's *already* exercised whenever eflomal isn't installed, and is a
   plausible second stage for a new decision rule in `align/aligner.py::_run()`: try eflomal, check
   diagnostic #1, fall back to the improved co-occurrence backend when eflomal's own confidence is too
   low — inverting the current "eflomal if available, cooccur only if unavailable" logic (`aligner.py:25-34`)
   into "eflomal if available *and* confident, else cooccur." This should be validated on Nyangbo
   itself before generalizing (see §4's type-sparsity risk — LLR doesn't help if the real problem is
   too few repeated word types, only if it's Dice's specific noise-sensitivity).
4. **[Medium priority, needs a verification spike first]** Investigate whether THOT's native `EFLOMAL`
   model type (via `sil-thot`, not the standalone PyPI `eflomal`) supports priors the way the
   standalone tool's `--priors`/`eflomal-makepriors` does. If yes: prime Nyangbo's alignment from a
   larger/related corpus's priors (candidate source: the largest-vocabulary corpus in the 18-language
   pilot, or another Kwa/Niger-Congo pair if one exists at larger scale) instead of aligning Nyangbo
   alone. If the Python wrapper doesn't expose this, this path requires dropping to the native THOT CLI
   directly — a materially bigger, riskier change than #1–#3, and should not be started until the
   spike confirms it's even possible.
5. **[Lower priority, narrow experiment only]** Subword sampling (arXiv:2012.11657) — promising
   published numbers but real added complexity and a conceptual tension with this repo's
   morpheme-level induction goals (§2). Worth a single narrow experiment on Nyangbo alone (the one
   broken case) before any broader investment, not a general pipeline change.
6. **[Out of scope, recorded for completeness]** Neural aligners (awesome-align, SimAlign) — hard
   constraint violation (torch/GPU), and independently likely non-functional for Nyangbo/Tutrugbu
   given its absence from mBERT/XLM-R pretraining data.

---

## 4. Open questions / risks

- **Is this actually an alignment problem, or a type-sparsity problem alignment can't fix?** Tutrugbu
  (Nyangbo) is described in the descriptive-linguistics literature as "highly agglutinative" with
  productive reduplication. A 1221-sentence corpus of a highly agglutinative language may have very few
  *repeated* word TYPES (each inflected form appears once or twice), which starves any co-occurrence-
  or EM/MCMC-based aligner of the repeated evidence it needs — regardless of whether the aligner is
  Dice, eflomal, LLR-competitive-linking, or (moot here) neural. If this is the real cause, none of §3's
  alignment-side fixes help; the actual fix would be morpheme-level pre-segmentation, which is circular
  since that's what this pipeline is trying to induce from the alignment in the first place. **Needs
  checking before investing further**: compute the token/type ratio for Nyangbo's 1221 sentences and
  compare it against the same statistic for 2–3 of the successful 18 languages (e.g. Vera'a, which is
  also Oceanic/low-resource but scored well) to see whether Nyangbo is a genuine outlier on this axis,
  not just on `glossed_frac`.
- **The eflomal-vs-fast_align-vs-GIZA++-at-hundreds-of-sentences comparison this doc needed doesn't
  exist in the published literature**, as far as this search found — every located comparison is either
  WMT-scale or same-toolkit-internal (including this repo's own `eflomal_vs_hmm.md`, which never
  varied corpus size). This repo is unusually well-positioned to produce that missing data point
  itself: it already has 18 languages at genuinely different corpus sizes (500–37,000 sentences) with
  `glossed_frac`-shaped statistics available or cheaply computable per §3.1. **Recommend mining the
  existing `PILOT_REPORT.md` data for a corpus-size-vs-glossed_frac correlation across all 18 languages
  as a free, in-house first check**, before any new engineering — if the relationship is smooth, that's
  evidence for a real data-volume floor (and suggests Nyangbo just needs more data, not a smarter
  aligner); if Nyangbo is a true outlier relative to its own corpus size, that's evidence for a
  language-specific cause (§4.1's agglutination hypothesis, or an orthography/data-quality issue in
  PolyGloss's Nyangbo rows specifically) rather than a generic small-corpus problem.
- **Whether `sil-machine`/THOT's Python wrapper exposes eflomal's priors mechanism at all is
  unverified** — this needs a direct read of `sil-thot`'s C++/Python binding source or docs before
  path #4 in §3 is even feasible to attempt, let alone implement.
- **The diagnostic threshold proposed in §3.1** (e.g., flag below ~5–10% `glossed_frac`) is eyeballed
  from one dataset's 55–96%-vs-0.2% split — a single hard outlier among 18 languages is not enough to
  know whether failure is a smooth continuum (making any hard cutoff somewhat arbitrary) or a genuine
  bimodal cliff (making thresholding easy and reliable). More languages/corpus sizes, or the §4.2
  in-house correlation study, are needed before this threshold should gate anything automatically
  rather than just warn.
- **Whether the LLR/competitive-linking upgrade to `cooccur.py` (§3.3) would help Nyangbo specifically,
  or just produce equally-noisy output faster**, depends entirely on which of §4.1's two hypotheses is
  correct — LLR is more principled than Dice under sparse *but present* co-occurrence counts, but no
  association-score reweighting manufactures repeated evidence that doesn't exist in the corpus. This
  should be tested empirically on Nyangbo before being adopted as a general recommendation for future
  thin languages, not assumed to generalize from the literature's larger-corpus results.
