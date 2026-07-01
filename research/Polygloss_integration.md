# PolyGloss Integration Plan (Idea 3 — curated pilot)

Uses the [PolyGloss corpus](https://huggingface.co/datasets/lecslab/polygloss-corpus) (353,266
hand-annotated IGT examples, 2,077 languages) as a **blind benchmark for our own symbolic
Hermit-Crab induction pipeline** — not as training data for a neural glosser, and not to reproduce
their model. We build our system (HC grammars via `induce/` + `align/`), score it against their
held-out `segmentation`+`glosses`, and — if a language earns it — keep the result as a real new
`golden_sets/<pair>/` entry, the same way tur/vie/hin/rus were added "for typological diversity."

**This doc scopes Idea 3 only** (a curated pilot of ~15–30 languages). Idea 2 (an automated sweep
across hundreds of languages to chart a data-volume scaling curve) is deferred — see §7.

---

## 1. Grounding facts (confirmed 2026-06-30)

- **Provenance — TRUE, with nuances.** PolyGloss aggregates ODIN (auto-scraped from published
  grammars — noisy *extraction*, hand-annotated *content*), SIGMORPHON-2023 shared-task data,
  IMTVault (LaTeX-extracted from Language Science Press grammars), and the Wav2Gloss "Fieldwork"
  compilation. No silver/LLM-generated glosses anywhere in the lineage — safe to treat as real gold,
  with an unquantified noise floor from the automatic extraction step.
- **Volume is heavily skewed.** Their own 9-language held-out set: Arapaho 36,776 train / Gitksan
  **89** train — a 400x spread within a set picked to be comparable. Corpus-wide average is
  ~170 examples/language across 2,077 languages, almost certainly thinner in the long tail.
- **Metalanguage (translation language) is not uniformly English.** No published distribution;
  expect real heterogeneity (Spanish for Latin American languages, French/German/Russian regionally).
  Filtering to English-metalanguage rows is the pragmatic way to reuse our English-pivot machinery
  without new work — see §5.
- **Schema** (`transcription, segmentation, glosses, translation, glottocode, language,
  metalang_glottocode, metalanguage, source, id`) uses `-`/`=` for affix/clitic boundaries — the same
  convention `engine/igt.py`'s `Morph.boundary` already uses. One row is one sentence; `segmentation`
  and `glosses` are whitespace-separated per word, morpheme-boundary-separated within a word.
- **Dataset access is gated** on Hugging Face (login + contact-info agreement). This is a real
  external blocker, not an engineering one — flagged wherever it matters below.

---

## 2. Non-goals

- Not adopting ByT5/LoRA fine-tuning, or any torch/GPU dependency — contradicts the repo's
  swappable-`IChatClient`, no-torch architecture decision (`research/README.md`).
- Not Idea 1 (reproducing their exact 9-language eval protocol/metric) — a smaller, separate task;
  this pilot can reuse most of the same loader code but optimizes for *durable golden-set growth*,
  not a leaderboard-comparable number.
- Not Idea 2 (2,077-language automated sweep) — see §7.
- Not touching `gold/compile.py`'s online-source compiler (UD/UniMorph/Wiktionary aggregation) — it
  solves a different problem (deriving gold from scratch) that PolyGloss's hand-annotated glosses
  make unnecessary for the languages we pick.

---

## 3. Where this plugs into the existing pipeline

```
polygloss-corpus (HF, gated) ──▶ corpus/polygloss/fetch.py ──▶ cached rows (per glottocode)
                                          │
                                          ▼
                          corpus/polygloss/convert.py
                    row → MorphWord list (engine/igt.py, reused)
                    row → ParallelRow (align/contract.py, reused)  [English-metalanguage rows only]
                          │                              │
                          ▼                              ▼
              corpus/polygloss/to_gold.py          align/aligner.py (reused, unchanged)
              held-out rows → wordforms.jsonl/            │
              lexicon.jsonl (gold/goldio.py schema)        ▼
                          │                        induce/tdd.py induction logic, via the
                          ▼                        §4.3 path adapter (small-corpus hyperparameters)
              golden_sets/pg_<glottocode>/                 │
              (NEW, frozen, committed)                     ▼
                          │                        HC grammar (engine/hc.py, reused)
                          └───────────────◄────────────────┘
                          corpus/polygloss/score.py
                    (adapted from gold/hc_validate.py — see §4 caveat)
                    parse_rate / lemma_recall / feature_recall vs held-out gold
```

`align/`, `engine/`, and `gold/goldio.py` are reused **unmodified**. `induce/tdd.py` and
`gold/hc_validate.py` both need small adapters, not code changes to those modules — see §4.1 and
§4.3. The net-new code is the PolyGloss-specific adapter layer (`corpus/polygloss/`).

---

## 4. Component-by-component plan

| Step | Reused (unmodified) | Net-new | Caveat |
|---|---|---|---|
| Fetch corpus rows for a glottocode | — | `corpus/polygloss/fetch.py` (HF `datasets` load + local JSONL cache) | Gated dataset — needs `huggingface-cli login` + accepting the corpus's access agreement. Not exercised by smoke tests (network+auth). |
| Row → segmented/glossed words | `engine/igt.py::Morph`, `MorphWord` | `corpus/polygloss/convert.py::to_morphwords()` | Straightforward: split `segmentation`/`glosses` on whitespace per word, then on `-`/`=` per morph, zip. |
| Row → alignable parallel pair | `align/contract.py::ParallelRow`, `corpus/ebible/read.py::tokenize()` | `corpus/polygloss/convert.py::to_parallel_row()` | Only meaningful for English-metalanguage rows (§5); `translation` is prose, `tokenize()` (already script-agnostic, Unicode-mark-aware) handles it. |
| Word alignment | `align/aligner.py::align()` (THOT Eflomal → Dice co-occurrence fallback) | — | No code changes. Per the repo-scaling audit, neither backend has a hardcoded minimum corpus size; Dice fallback is the realistic path below ~1,000 examples. |
| Grammar induction | `induce/tdd.py::run()`'s induction logic | small path adapter (§4.3) | **Not drop-in either.** `load_freqs`/`load_glosses` (`induce/tdd.py:46-60`) hardcode `EBIBLE = _RESEARCH/"_sources"/"ebible"` and read `PAIR_DIR[pair]/parallel.jsonl`+`glosses.tsv`. Also needs `n_roots`/`test_size` scaled down for small vocabularies (e.g. `≈50–100`/`≈20–30` vs. the eBible defaults of 300/120). |
| Held-out gold construction | `gold/goldio.py::write_gold()` (schema + writer) | `corpus/polygloss/to_gold.py` (row → `wordforms.jsonl`/`lexicon.jsonl` records) | **Design decision required** — PolyGloss's `glosses` field is a raw morpheme-gloss string, not pre-split into (lemma, features) the way our schema wants. See §5.1. |
| Scoring | HC-parse logic from `gold/hc_validate.py::validate()` | `corpus/polygloss/score.py` (adapted, standalone) | **`hc_validate.validate()` is NOT drop-in reusable as-is** — it calls `gold.hc_coverage._scripture_freqs(pair)`, which is wired to eBible scripture frequencies, and `--pair` is validated against `gold.compile.PAIR_DIR`, which is derived from `corpus.ebible.config.TARGETS`. Neither exists for a PolyGloss-only pair. The fix is to copy the parse/lemma/feature-recall scoring *logic* (lines ~50–90 of `hc_validate.py`) into a new function that computes frequency from the PolyGloss rows themselves instead of scripture — not a config change, a ~40-line adapter function. |

### 4.1 Why `hc_validate.py` needed adaptation, not just a new `--pair` entry

`gold/compile.py:46-51` builds `PAIR_DIR = {k: f"{ENGLISH_ID}__{v}" for k, v in TARGETS.items()}` —
directly from the eBible target registry. `gold/hc_validate.py::validate()` calls
`_scripture_freqs(pair)` (from `gold/hc_coverage.py`) to rank wordforms by frequency before sampling.
Both assumptions are eBible-specific. Rather than bend the eBible registry to accept non-eBible pairs
(which would blur "eBible target" as a concept), `corpus/polygloss/score.py` reimplements the same
recall logic against frequencies computed directly from the PolyGloss rows' own token counts.

### 4.2 The gloss-splitting design decision

To build `wordforms.jsonl`-shaped gold (`{surface, lemma, pos, features, source}`) from a PolyGloss
`(segmentation, glosses)` pair, each morph gloss must be classified lexical (contributes a lemma) or
grammatical (contributes a feature). We use the **Leipzig Glossing Rules convention that grammatical
category labels are capitalized** (`INTERJ`, `ZERO`, `ART`, `1SG`, `PL`, …) while lexical glosses are
lowercase, often dotted for multi-word translations (`you.know`). Concretely:
`is_grammatical(tag) = tag.replace(".", "").replace("_", "").isupper()`. The word's lemma is keyed off
its first non-grammatical (stem) morph; every grammatical morph's tag becomes a feature-bundle entry.

This is a **simplified feature representation** — a sorted tuple of grammatical tags, not yet
converted to `gold/inflection.py::canon()`'s canonical feature-bundle format. That conversion is
scoped as a follow-up once a candidate language is picked (§6), not attempted generically now, since
`canon()`'s feature vocabulary is itself derived from UniMorph and may not map 1:1 onto whatever
feature tags a given grammar's original author chose.

### 4.3 Feeding a picked language into `induce/tdd.py` without touching it

Two options once a real pilot language is picked, neither implemented yet (§6 marks this pending):

- **(a) Impersonate an eBible pair** — write `corpus/polygloss/build.py` output (`parallel.jsonl` +
  `glosses.tsv`, same shape as `corpus/ebible/build.py`) into a real `_sources/ebible/<name>/`
  directory and add a matching entry to `induce.tdd.PAIR_DIR` (a plain module-level dict, mutable at
  call time) before calling `run()`. Zero changes to `tdd.py`, but the directory naming is
  misleading (PolyGloss data sitting under an "ebible" folder) — workable for a quick pilot run, not
  something to leave as a permanent layout.
- **(b) Parametrize `load_freqs`/`load_glosses`** to accept an explicit corpus directory (or
  in-memory `Counter`/gloss-dict) instead of hardcoding `EBIBLE`. The right long-term fix, but it
  touches a module the current 8-language product path depends on — do this deliberately, reviewed,
  not as a side effect of the PolyGloss pilot.

Given the load-bearing nature of `tdd.py`, this plan defaults to (a) for the first real pilot run and
defers (b) until there's evidence the pilot is worth investing in further.

---

## 5. Language-selection criteria (for when HF access is available)

Pick ~15–30 languages meeting **all** of:

1. **Volume floor**: ≥500–1,000 train examples (per the repo-scaling audit, TDD induction is
   *viable* below this with scaled-down hyperparameters, but coverage plateaus fast and single-run
   scores get noisy; 89-example languages like Gitksan are not worth attempting here — that finding
   already came out of Idea 1's scope, not this one).
2. **English metalanguage** (`metalang_glottocode` == English's glottocode, or `metalanguage ==
   "English"`), verified per-language once HF access exists — reuses the pivot-language assumption
   already baked into `corpus/ebible/read.py`'s tokenizer choice and, more importantly, avoids
   silently mixing metalanguages within one pair's evidence.
3. **Typological gap-filling** relative to the current 8 (swh/ind/tgl/spa/tur/rus/hin/vie), which
   skew Bantu/Austronesian/Romance/Turkic/Slavic/Indo-Aryan/isolating. Candidates that add real
   diversity: polysynthetic (Arapaho-like, if volume allows), ergative (Tsez/Lezgi-like), or other
   families entirely absent from the current 8.
4. **Not already in the current 8** (no point re-benchmarking swh/ind/tgl/spa/tur/rus/hin/vie against
   themselves, though checking whether they *appear* in the full 2,077-language corpus is a useful
   sanity check — if any of the thin golds (tur/vie/hin/rus) show up, their PolyGloss rows are
   higher-quality gold than our THOT-induced `alignment_glosses.jsonl` and worth a look independent
   of this pilot).

This selection step is a manual judgment call, not automated — deliberately, since criterion 3 needs
a linguist's read on what "typological gap" actually means, not a script.

---

## 6. Build order / status

1. **DONE (this session)** — `corpus/polygloss/` package, offline-testable end to end (`pytest
   corpus/polygloss/` — 8/8 passing, no network, no `hc` binary required):
   - `schema.py` — `PolyglossRow` dataclass matching the HF column names.
   - `convert.py` — `to_morphwords()` (row → `engine/igt.py::MorphWord` list, skipping
     segmentation/gloss tier mismatches rather than guessing), `is_grammatical_gloss()` (the Leipzig
     all-caps heuristic, §4.2), `stem_and_features()` (lexical/grammatical morph split),
     `is_english_metalanguage()` (the §5 metalanguage filter), `to_parallel_row()` (row →
     `align/contract.py::ParallelRow`, reusing `corpus/ebible/read.py::tokenize()`).
   - `to_gold.py` — `rows_to_wordforms_and_lexicon()` + `write_pilot_gold()`, producing
     `wordforms.jsonl`/`lexicon.jsonl`-shaped records via `gold/goldio.py::write_gold()` unmodified,
     with `lemma` keyed the same way `goldio.load_gold()` already expects (surface stem form, not a
     synthetic id).
   - `score.py` — `score_parses()` (pure parse/lemma/feature-recall logic, adapted from
     `hc_validate.py`, unit-tested against a fake `parses` dict) + `score_pair()` (the thin driver
     that actually calls `engine/hc.py::run_parse`, not exercised offline).
   - `fetch.py` — `fetch_language()`/`load_cached()` against `lecslab/polygloss-corpus` via the `datasets`
     library; raises a clear error if `datasets` isn't installed or the HF gate blocks access.
   - `tests_smoke.py` — the Vera'a example from the paper's own research, exercising every
     conversion/scoring function above, plus a deliberately-misaligned fixture row to confirm
     mismatched tiers are skipped rather than silently mis-parsed.
   - `research/pyproject.toml` — added a `polygloss = ["datasets>=2.19"]` optional-dependency group
     (`uv sync --extra polygloss`), matching the `align`/`audio`/`data-prep` extras pattern; kept out
     of core deps since it's not needed until real HF fetches happen.
2. **DONE (2026-07-01)** — HF access was already available (a cached token on this machine had
   already accepted the corpus's gate); `huggingface-cli login` was not needed. Loaded the full
   corpus (train=340,251 / test=6,867 / dev=6,148 rows, 2,077 glottocodes) and computed per-language
   English-metalanguage counts to apply §5's selection criteria. Only 9 glottocodes have the corpus's
   own `test`/`dev` splits (its SIGMORPHON-2023 held-out set); of those, Gitksan (89 rows, below the
   volume floor) and Uspanteko (0 English-metalanguage rows — Spanish-metalanguage corpus) were
   excluded, leaving 7 contamination-free candidates. Picked 18 languages total (7 test-split + 11
   train-holdout) for real typological gap-filling against the current 8 (Bantu/Austronesian/Romance/
   Turkic/Slavic/Indo-Aryan/isolating): Algonquian (Arapaho), Nakh-Daghestanian ergative (Tsez,
   Lezgian, +isolate ergative Basque), Niger-Congo Kwa (Nyangbo), isolate polysynthetic (Ainu),
   non-Swahili Bantu (Ruuli), Oceanic (Vera'a, Natügu), Iroquoian (Cayuga), Gyalrongic (Japhug),
   Cushitic (Beja), Turkic-Siberian (Dolgan), Samoyedic (Kamas, Selkup), Tuu/Khoisan click (N‖ng),
   Trans-New Guinea (Mauwake), Papuan isolate (Kalamang). See `run_batch.py::LANGUAGES`.
3. **DONE (2026-07-01)** — built the §4.3(a) impersonate-a-pair adapter (`build.py`: fetch → filter
   English metalanguage → `align.aligner.align()` gold-blind → write `_sources/ebible/pg_<glottocode>/`
   + register in `induce.tdd.PAIR_DIR`) and the pilot driver (`pilot.py::run_pilot`, auto-scaling
   `n_roots`/`test_size` with vocabulary size — a flat root count isn't comparable across an 800-word
   and a 36k-row corpus) and batch runner (`run_batch.py`, one failure can't abort the batch, writes
   `out/PILOT_REPORT.md`). Ran all 18 languages (150s induction budget each, ~185s wall-clock
   including fetch/align/score) — **18/18 succeeded, 0 failed**. See `corpus/polygloss/out/
   PILOT_REPORT.md` for the full table; internal HC coverage ranged 0.44-0.93, gold `lemma_recall`
   0.00-0.29. One genuine finding: Nyangbo's THOT alignment produced a real English gloss for almost
   no induced root (`glossed_frac=0.002` vs. 0.55-0.92 for every other language) at this corpus size/
   budget, so its near-zero lemma/feature recall reflects alignment starvation, not a segmentation
   failure — recorded honestly in the report rather than hidden or averaged away.
4. **DECIDED AGAINST automatic promotion** — `build_pilot` originally wrote `golden_sets/pg_<
   glottocode>/` as a side effect of every scoring run; corrected so scoring reads gold in-memory
   (`build_pilot` returns `gold_wordforms`/`gold_lexicon` directly) and `golden_sets/` is untouched by
   a benchmark run. `build.py::promote_golden_set()` exists for a deliberate, later call once a human
   reviews a language's score and decides it earns a frozen golden set — no language has been promoted
   yet (this pilot's scores, mostly optimistic train-split upper bounds or gloss-starved, don't clear
   a bar strong enough to justify it without closer review).
5. **STILL PENDING** — feature-bundle canonicalization (§4.2) for any language that eventually gets
   promoted (step 4), once we've seen what its actual grammatical-tag vocabulary looks like.

---

## 7. Idea 2, deferred

An automated sweep across hundreds/thousands of PolyGloss languages to chart an
induction-quality-vs-example-count scaling curve remains a legitimate follow-on question, but it
needs actual language-onboarding automation that doesn't exist yet (per the repo-scaling audit,
adding a language today is a manual `TARGETS`/`SEED` dict edit, not a script), and it's scoped like a
standalone research artifact rather than a repo feature. Revisit after this pilot has real results —
if the pilot's languages mostly succeed, that's evidence Idea 2's engineering investment would pay
off; if most stall out even above the 500–1,000-example floor, that's evidence the floor needs to be
higher and a blind sweep would mostly produce noise.
