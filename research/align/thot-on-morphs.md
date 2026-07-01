# THOT-on-morphs — investigation plan

**Question.** Does running THOT/eflomal over morpheme-level tokens on *both* sides (English included, not
just the target) — with known **classes** (natural/harmony classes, POS/MSA, slot templates) used to
constrain which morphs get pooled as statistical evidence — improve the **core TDD-for-grammar algorithm**
(`induce/tdd.py`'s Red→Green→Refactor loop + `induce/cotrain.py`'s THOT↔HC root-discovery extension)? Not
"does it raise an internal alignment self-agreement metric" (that's `align/eflomal_vs_hmm.md`'s question,
already answered) — does it make the **induced grammars** better: higher coverage, lower ambiguity, higher
gold recall, less enumeration debt, on all 8 pairs (`swh ind tgl spa tur rus hin vie`).

This doc is a plan, not a result. No paradigm below has been run yet.

---

## 0. Where the pieces already are

- `align/morph_align_hc.py::build_streams` already segments the **target** side into HC-verified morphemes
  and flattens them into `morph_rows` before calling `align()`. English (`src`) stays whole-word.
- `induce/cotrain.py::_align_table` calls that exact `build_streams`, so **the THOT↔HC co-training loop
  already aligns target-morphemes ↔ English-whole-words** — this is the true current baseline for
  "THOT on morphs," not plain word-level alignment. `propose_roots` uses the resulting table to gap-fill
  unparsed words as new roots, gated by coverage + ambiguity (`cotrain()`'s guard).
- `induce/tdd.py`'s own affix/root induction (`affix_candidates`, `grow_roots`, `assign_slots`) has **no
  cross-lingual signal at all** — it's pure surface-frequency/residue statistics over the target side only.
  THOT only enters via the separate `cotrain.py` layer.
- Class/feature machinery that already exists but isn't wired into alignment:
  - `induce/phonology.py::HARMONY_CLASSES` + `collapse_families` — collapses vowel-harmony allomorph
    *surface* variants (Swahili causative `-ish-/-esh-`, stative `-ik-/-ek-`) into one archiphoneme +
    conditioning natural class. Only `swh` has a `HARMONY_CLASSES` entry today; `tur` (also harmonic) does
    not yet.
  - `induce/tdd.py::assign_slots` — learns each affix's morphotactic **slot** ordinal and its **MSA**
    (`req_pos`, the POS class it attaches to) from co-occurrence evidence, used today only to prune the
    *parse* search space (templated grammar), never to prune *alignment* evidence.
- `align/eflomal_vs_hmm.md` is the methodological precedent to follow (and to distrust correctly): its own
  first-pass result was a metric bug, not a real aligner difference. Any "paradigm X wins" claim here needs
  the same hand-diff-a-sample discipline before being trusted.

---

## 1. Why naive symmetric segmentation risks making things *worse* (the explosion)

These are low-resource verse corpora (400–~9,000 verses/pair; PolyGloss's own provenance note puts a
400× volume spread as normal for this class of data). Segmenting **both** sides into morphemes multiplies
the number of distinct token *types* while shrinking the token *count* backing each type — exactly the
sparse-data regime `eflomal_vs_hmm.md` already flags as the reason eflomal (a Bayesian HMM extension) beats
plain HMM here. Splitting English too, with no constraint, adds a second source of sparsity on top of the
target's — more short, ambiguous, ambiguous-to-each-other tokens, more spurious many-to-many candidate
pairs, for the same evidence budget.

The literature's own fix for this at scale is never "segment blindly and hope the aligner copes" — it's
segmentation *plus* a way to keep the effective vocabulary small: BPE gets away with unconstrained
splitting only because NMT training corpora are orders of magnitude larger; morphologically-informed work
(factored translation models, Habash & Sadat's matched Arabic/English segmentation schemes) instead uses
**linguistic classes** to keep the token inventory small relative to the corpus. This repo already has that
mechanism for the *parse* side (`collapse_families`, `assign_slots`) — the concrete idea this investigation
tests is: reuse those same classes to pool **alignment** evidence, so THOT counts co-occurrences over
`(archiphoneme-class, slot)` identities instead of raw surface morph strings wherever a class is known,
and falls back to raw surface forms only where it isn't. That is the literal answer to "use classes and
phonemes to constrain the statistics."

---

## 2. Paradigms to test

Each paradigm is a tokenization + evidence-pooling policy, run through the **same** consumer
(`cotrain.py`'s root-proposal loop, plus a comparable hook into `tdd.py`'s affix induction — see §4). All
of them are strict supersets of engineering effort on top of the one before.

| | Target tokens | English tokens | Evidence pooling | Status |
|---|---|---|---|---|
| **P0** | whole word | whole word | none (no THOT signal in `tdd.py` at all) | exists (production default without cotrain) |
| **P1** | HC morphemes | whole word | none (raw surface `table.best()`) | exists (`cotrain.py` default today — the real baseline) |
| **P2** | HC morphemes | unsupervised morphemes (Morfessor/BPE, trained on English NT text) | none | net-new |
| **P3** | HC morphemes, canonicalized to `(class, slot)` where known | same canonicalization applied to any English morph that lines up with a classed target morph | class-constrained pooling | net-new |
| **P4** | HC morphemes | guided split: English split only where P1 evidence recurs ≥N times pointing at two sub-spans of one English word | class-constrained pooling (P3's mechanism) | net-new |

- **P2** is the "just segment both sides statistically" paradigm from the prior research turn — cheapest to
  build, no linguistic resource, but per §1 the most exposed to the explosion risk.
- **P3** is the direct answer to "use classes/phonemes/features to constrain the statistics": before
  `propose_roots`/`table.best()` count a target morph as evidence, map it through
  `induce.phonology.collapse_families`'s output (if its harmony family was collapsed) and through
  `assign_slots`' learned `req_pos`, so e.g. Swahili `-ish-` and `-esh-` contribute to ONE alignment bucket
  instead of splintering the (already scarce) evidence for "causative" across two surface strings.
- **P4** is Fraser (2009)'s *guided* segmentation, adapted to not require any independent English
  morphology model at all — it only trusts a split where the *target* side already gives repeated,
  class-tagged evidence that one English word is doing two jobs (e.g. consistently co-occurring with both
  a root-slot morph and a recurring case/aspect-slot morph across many verses). Minimal new assumptions,
  directly reuses machinery this repo already trusts (`assign_slots`' slot/MSA evidence).

**Deliberate controls:**
- **Vietnamese (`vie`)** is isolating (≈no morphology) — P0 through P4 should converge to ~the same
  numbers, since there's almost nothing to segment. If they *don't* converge, that's a harness bug, not a
  linguistic finding — check this before trusting any other pair's result.
- **Turkish (`tur`)** is the sharpest positive-hypothesis case for P3: agglutinative + vowel harmony, the
  same phenomenon `HARMONY_CLASSES["swh"]` already models. `tur` has no `HARMONY_CLASSES` entry yet —
  adding one (from its harmony vowel pairs) is a small prerequisite side-task, not part of the paradigm
  code itself, and should be called out as such in the results (a `tur` P3 result without this entry is
  not testing what it claims to).

---

## 3. Metrics (what "improvement in the core TDD algorithm" means, operationally)

Measured identically across paradigms, per pair, holding the seconds/sample budget fixed:

1. **Coverage** — `induce.tdd.coverage()` parse rate on a held-out frequent-wordform set. Primary
   Red→Green signal.
2. **Ambiguity** — `coverage()`'s second return (mean parses/word). A coverage "win" that pushes ambiguity
   toward/over the existing `amb_cap` is disqualified, per the discipline already baked into
   `tdd.run`/`cotrain.cotrain`.
3. **Gold recall / gold parsed** — `induce/gold.py::score_gold`, wherever a real gold set exists
   (`golden_sets/{swh,ind,tgl,spa}` have full `wordforms.jsonl`/`lexicon.jsonl`; `tur/rus/hin/vie` currently
   only have `derived_pos.json` — treat those four as **gold-unavailable, coverage/ambiguity-only** results
   and say so plainly rather than reporting a misleadingly-precise number).
4. **Root/affix yield and precision** — count of new roots/affixes each paradigm proposes, and (where gold
   exists) the fraction whose proposed gloss matches gold.
5. **Enumeration debt** — `induce.phonology.enumeration_debt` / `harmony_families`. P3 succeeding should
   show this **drop** relative to P1/P2 — a direct, independent check that the class-constraint mechanism
   is doing its job, not just a side effect of a coverage change.
6. **THOT∩HC accept rate** — the existing `eflomal_vs_hmm.md` metric. Kept only as a **secondary
   diagnostic** of the alignment layer's internal agreement, explicitly demoted from "the" success
   criterion for this investigation (that question is already answered; this one is about downstream
   grammar quality).
7. **Wall-clock / iterations-per-second** — same budget per run; report the tax of shorter, more numerous
   morpheme tokens explicitly, since P2–P4 do more alignment work per verse than P0/P1.

---

## 4. What needs to be built (net-new, kept minimal)

- **`align/segment_en.py`** (new) — pluggable `segment(tokens: list[str]) -> list[list[str]]`, three
  strategies: `identity` (P1, already what happens today), `unsupervised` (P2 — Morfessor or a small
  frequency-capped BPE trained on the pair's English NT text; pure-Python, no GPU/torch, consistent with
  this repo's dependency stance), `guided` (P4 — consumes P1's alignment table + `assign_slots` evidence to
  decide split points, no independent English morphology resource). `contract.ParallelRow` is already just
  `(list[str], list[str])`, so nothing in `align/aligner.py`/`backends.py` needs to change to accept this.
- **`align/class_key.py`** (new, for P3) — `class_key(morph_form, kind, pair) -> str`: looks up
  `induce.phonology.collapse_families`'s collapsed-family membership and `assign_slots`' learned `req_pos`
  for a morph, returns a canonical bucket id, or the raw surface form when no class is known (graceful
  fallback — P3 never does *worse* than P1 on morphs it has no class evidence for). A thin wrapper around
  `cotrain.propose_roots`/the alignment table uses this to pool `table.best()` evidence by bucket instead of
  by surface string.
- **`align/run_paradigm_study.py`** (new, the harness) — for each of the 8 pairs × the paradigms that apply
  (P0/P1 need no new code; P2–P4 need the modules above), runs `cotrain.cotrain(...)` (or a thin variant
  wired to the paradigm's tokenization) with a **fixed** seconds/sample budget, then scores the resulting
  model with `coverage()` + `score_gold()` (where available) against a **held-out set frozen once per pair**
  (same test words across all its paradigms — critical, or differences are attributable to sampling, not
  the paradigm). Writes `align/out/thot_on_morphs/<pair>_<paradigm>.json`.
- **`tur` `HARMONY_CLASSES` entry** (small prerequisite for a meaningful P3 result on `tur`) — Turkish
  front/back (and, if attempted, rounding) vowel harmony pairs, mirrored off the existing `swh` entry's
  shape in `induce/phonology.py`.

Nothing here requires modifying `align/aligner.py`, `align/backends.py`, or `align/contract.py` — the
existing `list[str]`-in-list[str]-out contract already supports arbitrary token granularity on either side.

---

## 5. Procedure

Per pair:
1. Freeze a held-out test-word list to disk once (reuse `tdd.seed`'s held-out selection logic, just persist
   it instead of recomputing per run).
2. Run **P0** (`tdd.run` with no `cotrain`) — reproducible today, no new code. This is the floor.
3. Run **P1** (`cotrain.cotrain` default settings) — reproducible today, no new code. This is the real
   baseline the new paradigms must beat.
4. Build and run **P2**, then **P3**, then **P4** (each layers on the last).
5. For every pair × paradigm, record all §3 metrics.
6. Compare **within a pair** across its paradigms only — not across pairs (corpus sizes differ up to
   ~20× among the 8, let alone PolyGloss-scale spreads) — and write the findings up in
   `eflomal_vs_hmm.md`'s own style: a results table, then an honest verdict section that actively tries to
   debunk the apparent winner before accepting it (see §6).

---

## 6. Risks / known traps (lessons already paid for once in this repo)

- **Metric artifacts.** `eflomal_vs_hmm.md`'s first pass showed a 7-point "win" that was entirely a bug in
  `_agrees()`'s substring fallback. Before declaring any paradigm a winner here, hand-diff a sample of its
  new root/affix proposals against the previous paradigm's, the same way that investigation did.
- **Ambiguity-cap gaming.** Never report a coverage delta without its paired ambiguity number — a paradigm
  that "wins" by drifting ambiguity toward the cap is not a real improvement.
- **Held-out contamination.** `tdd.py`'s moving-window curriculum promotes tested words into roots as it
  goes; make sure the frozen held-out set (step 5.1) is treated identically (not silently consumed at
  different rates) across paradigms for the same pair.
- **The `vie` sanity check (§2) is not optional.** Run it first, every time the harness changes.
- **Negative results are the expected, useful outcome for P2 in particular.** The literature's own subword
  gains are demonstrated at NMT-scale corpora (millions of sentences); at 400–9,000 verses, P2 (unconstrained
  symmetric segmentation) may well *regress* coverage/gold recall on some or most pairs. That is a valid,
  reportable finding — it is the argument *for* needing P3's class constraints, not a failure of the
  investigation. Write it up either way.
- **`tur` P3 without the `HARMONY_CLASSES` prerequisite (§2, §4) is not a real P3 run** — flag any such
  result explicitly rather than let it read as "P3 doesn't help agglutinative languages."

---

## 7. References

**Morpheme/subword segmentation for alignment & SMT (the "is this done, how" grounding):**
- Fraser, A. (2009). *Deeper than Words: Morph-based Alignment for Statistical Machine Translation.*
  — the guided-vs-unguided segmentation distinction P4 adapts.
- Koehn, P. & Hoang, H. (2007). *Factored Translation Models.* EMNLP-CoNLL.
  — the class/factor-stream idea generalized here into alignment-evidence pooling (P3).
- Creutz, M. & Lagus, K. — Morfessor: *Unsupervised morpheme segmentation and morphology induction from
  text corpora using Morfessor 1.0*; *A Language-Independent Unsupervised Model for Morphological
  Segmentation.* — the unsupervised segmenter candidate for P2.
- Habash, N. & Sadat, F. — Arabic preprocessing/segmentation-scheme matching for SMT — the precedent for
  matching segmentation schemes across a language pair rather than segmenting each side independently.
- Amharic↔Tigrigna SMT study using Morfessor + GIZA++ — real BLEU gain from unsupervised morph segmentation
  on both sides at comparable low-resource scale to this project's corpora.
- *A Hybrid Morpheme-Word Representation for Machine Translation of Morphologically Rich Languages*
  (arXiv:1911.08117) — word-boundary-aware morpheme-level phrase extraction.

**IGT / gloss-line pivot alignment (relevant since this repo's segmentation ground truth — HC's gloss
line, and PolyGloss's hand-annotated gloss lines — is itself a form of pre-existing morpheme alignment):**
- Lewis, W. & Xia, F. — ODIN (Online Database of Interlinear Text).
- Georgi, R., Xia, F., Lewis, W. — INTENT toolkit (automatic word alignment + POS projection over IGT
  gloss/translation lines).

**Internal precedent (methodology to reuse, not re-derive):**
- `align/eflomal_vs_hmm.md` — the accept-rate measurement methodology, and its own cautionary history of a
  metric bug producing a false "winner." Follow the same before/after + hand-diff discipline here.
- `research/Polygloss_integration.md` §1 — the "thin gold" framing for `tur/rus/hin/vie`, reused verbatim in
  §3's gold-recall caveat above.
- `induce/README.md` — the Red→Green→Refactor framing, the two-sided-induction coverage jump
  (`swh 0.26→0.64` etc.), and the existing harmony-class/slot/MSA machinery §1 and §4 build on.
