# research/

**Stage 1 — the Python research playground** (see the repo-root README's maturity stages). Ideas are
proven here against the golden sets before the C# validation program (`src/`) inherits the proven pieces.
Offline-first: provider-agnostic LLM harness, no torch/GPU, THOT for alignment, HermitCrab for parsing.

---

## The system in one picture

The job is to take an unknown language's parallel text and **produce grammatical analyses a human can
trust** — with the easy parts auto-approved and the hard parts written up as good reports for review.

```
                         ┌─────────────── TWO GOLDEN SETS (validate from opposite ends) ──────────────┐
   parallel corpus       │  golden RULES  golden_sets/<lang>/   ── validates ──►  LEAF output         │
        │                │  golden REPORTS review/paradigm/golden/ ── validates ──►  TRUNK output      │
        ▼                └────────────────────────────────────────────────────────────────────────────┘
  HC parse + THOT align
        │
        ├──► LEAF  (the easy, high-volume work — "auto-approve")
        │      induce → cotrain → emit confidence-routed deltas
        │      review/deltas/  ·  ≥0.85 accept (auto) / 0.5–0.85 review / <0.5 defer
        │      validated by the golden RULES (did we reproduce the true lexicon/morphology?)
        │
        └──► TRUNK  (the hard, structural work — "prepare a great report, ask a human")
               explore A/B/C+fit  →  packet (THOT+HC+explorer)  →  Gemma report  →  Opus review
               review/paradigm/  ·  progressive layers: switches → inventory → agreement → exceptions
               validated by the golden REPORTS (did Gemma synthesize a good, faithful report?)
```

- **Golden RULES** (`golden_sets/<lang>/`) are the *backdrop truth* — the real lexicon + inflection
  classes + a wordform oracle the leaf must reproduce. Frozen, committed, read-only by convention.
- **Golden REPORTS** (`review/paradigm/golden/`) are the *optimization target* — the best paradigm
  report we can write by hand (the ceiling). The trunk's report is scored against it.
- They meet — full end-to-end cross-check — **only on swh today** (the one language with both rich rules
  *and* report goldens). See `docs/remaining-work.md`.

---

## Where we are (honest, 2026-06)

8 languages: swh, ind, tgl, spa (original) + tur, vie, hin, rus (added for typological diversity).

**Leaf** — wired for all 8; the delta store is populated (16,194 ops total). But auto-approve is currently
low: **~5% accepted, ~72% review, ~24% deferred** — most ops are mid-confidence, so the leaf isn't yet
carrying the easy bulk on its own.

**Trunk** — the report pipeline spans **7 detector families** across the 8 languages, honestly measured.
Scored anchors (10 across 6 languages, spanning easy→hard morphology):
| family | anchor | completeness | faithfulness | reads as |
|--------|--------|------------:|------------:|----------|
| Bantu noun-class | swh | 1.0 | live Gemma 0.63–0.75 | evidence all present; improve generator |
| Bantu concord | swh | 1.0 | 1.0 | strong |
| gender-number | spa | 1.0 | 1.0 | gender via determiner agreement (-o→el,-a→la)+number -s; 8/8 vs WALS |
| TAM (3 realisations) | swh/spa/rus/tur/vie/ind | 0.4–1.0 | 1.0 | prefix (swh na/li/ta), suffix (spa -ndo/-ó, rus -л, tur -dI), analytic particles (vie đã/sẽ/đang, ind sudah/akan/sedang) |
| analytic np-case | tgl | 1.0 | 1.0 | ang→nsubj, ng→nmod, sa→obl; core-arg test rejects spa/swh look-alikes |
| analytic np-case | hin | 0.83 | 1.0 | postpositions को/से/का/में/लिये via their English-adposition alignment (ने ergative missed) |
| voice-focus | ind | 1.0 | 1.0 | passive di- (pivot) + active meN- recovered from **internal complementary distribution** |
| isolating | vie | 1.0 | 1.0 | "correctly find nothing" — monosyllabic ⇒ no inflection (also fixes the synthesis switch) |
| possessive/number | tur | 0.5 | 1.0 | plural -lAr recovered; possessor agreement unmarked in English |
| suffixal case (agglut.) | tur | 0.33 | 1.0 | nom/dat/loc; English pivot lumps the obliques |
| suffixal case (fusional) | rus | 0.33 | 1.0 | nom+instr; fusional endings need a declension-table detector |
| number (fusional) | rus | 0.5 | 1.0 | plural -ов/-ев recovered; case×number fusion blurs the rest |

Each detector follows one recipe: a covariation signal (suffix/ending/affix vs projected role or feature,
an adjacent agreement marker, **or vernacular-internal complementary distribution** for what the English
pivot can't see) + a **layer-0 switch gate** that kills cross-paradigm false-positives. All cached for
reproducibility. **Live Gemma** (not heuristic) faithfulness across the clean anchors is 0.63–1.0
(mean ~0.93). A **report-review step** (`report_review.py`, firewall) then issues per-cell
promote/defer/reject — the trunk's decision stage — and a promoted paradigm is recorded `confirmed` on
its profile.

The metric is **separable on purpose**: `completeness` measures the detector/packet, `faithfulness`
measures Gemma — every gain attributes to a specific fix. Two recent engine hardenings:
- **Role-aware completeness** — a golden case-cell is credited only when a packet family has the marker
  *and* a matching projected role, so coincidental marker overlap no longer over-credits (fusional rus
  fell from a fake 0.5 to an honest 0.33).
- **Reproducible detector** — the case detector's vote tallies are disk-cached per (lang, sample), so the
  metric is stable across runs (THOT alignment is otherwise stochastic) and fast (no re-train).

The Turkish case detector (the suffixal mirror of the Bantu concord explorer) flips the `case` switch and
unlocks `tur.case` in the progressive graph; 8-lang case spot-check vs WALS = 6/8 (vie/hin misses are
documented upstream issues).

**System snapshot** — `python -m review.paradigm.sweep` walks every language's *unlocked* paradigms
(progressive cascade: learning a layer unlocks the next in the same pass), scores against any golden, and
records onto the profiles: 33 paradigms — **19 scored** (mean 0.77) across **all 8 languages**, 7 locked,
3 no-builder, 4 generated (runs but no golden yet). This is the data the review UI will read.

> **Tokenizer note (2026-06):** the eBible tokenizer used `\w+`, which drops Unicode Mark characters
> (Devanagari matras) — so every Hindi word was shattered into consonant fragments and the whole hin
> pipeline ran on garbage. Fixed (`corpus/ebible/read.py`: mark-inclusive regex + NFC). Re-ingest with
> `python -m corpus.ebible.build --pair hin --no-fetch`. Only hin was affected (others are precomposed).

See `learning_paradigms_plan.md` for the trunk design + the per-language paradigm backlog, and
`docs/remaining-work.md` for the roadmap, cleanup list, and the (coming) Streamlit review UI.

---

## Packages (current layout)
| Package | What it is |
|---|---|
| `corpus/` | the parallel-text substrate (eBible ingest) |
| `engine/` | the HermitCrab grammar engine + `hc` CLI driver (`engine/hc.py`) |
| `gold/` | golden-set compiler/loader + HC-validated word→gloss round-trip + reference compile |
| `golden_sets/` | **golden RULES** — the frozen per-language lexicon/morphology oracle (see its README) |
| `induce/` | the TDD induction cycle + THOT↔HC co-training (`tdd.py`, `cotrain.py`, `accumulate.py`) |
| `align/` | statistical word/morpheme alignment (THOT Eflomal via `sil-machine`, co-occurrence fallback) |
| `propose/` | the propose core (`Case → ChangeSet`) + `harness/` (provider-agnostic `LLMClient` + registry) |
| `review/` | **the review layer** — see below |
| `review/deltas/` | **LEAF** — the confidence-routed delta store (the write source-of-truth; see its README) |
| `review/deferrals/` | resolution-ticket system + the typological switch detectors (`profile_detect.py`) |
| `review/paradigm/` | **TRUNK** — packet → Gemma report → score-vs-golden → per-language profiles |
| `assess/` | grammar-quality metrics (MDL, scorecard, ablation ranking) |
| `eval/` | golden eval runner + benchmarks (LingGym calibration) |
| `addons/` | optional `audio/` evidence + `bilingual/` Apertium bridge (not first-class) |
| `deferrals/`, `deltas/` (root) | git-tracked DATA (tickets; a legacy delta path) — see remaining-work note |

---

## Environment (uv)
Managed with **[uv](https://docs.astral.sh/uv/)**; deps pinned in `uv.lock`. `requires-python` is
`>=3.10,<3.14` (upper bound from `sil-machine`). No torch/transformers/GPU.

```bash
cd research
uv sync                    # core (anthropic, httpx)
uv sync --extra align      # + sil-machine[thot]>=1.9 (THOT Eflomal) for alignment
uv sync --extra audio      # + allosaurus / faster-whisper (optional phone evidence)
uv sync --extra data-prep  # + flexlibs (Windows + FieldWorks only)
```

## Running things
Run from `research/`. Highlights:
```bash
# TRUNK — one paradigm report, scored against its golden, recorded onto the profile
python -m review.paradigm.run --pair swh --paradigm noun-class --endpoint heuristic   # offline
python -m review.paradigm.run --pair tur --paradigm case --endpoint local             # live Gemma (localhost:8080)
python -m review.paradigm.profiles --lang swh                                          # progressive state + next-unlocked

# LEAF — accumulate the cycle and route deltas by confidence
python -m induce.accumulate --pair spa --rounds 3 --seconds 60
python -m review.deltas.build_store --pair spa --round 1

# golden RULES validation
python gold/reference/hc_validate.py --pair spa --grammar class
```

## Tests
Tests are named `tests_*.py`; `pyproject.toml` configures pytest to collect them, so plain `pytest` works:
```bash
pytest review/ induce/ align/        # 205 pass (incl. 15 paradigm-pipeline tests)
pytest review/paradigm/              # the trunk pipeline
```

## Serving local models
`../serving/` runs a `llama-server` behind an OpenAI-compatible endpoint the harness drives (`local`
endpoint = `localhost:8080`). For the report path, the harness disables server-side thinking so the model
emits the structured answer. `opus` needs `ANTHROPIC_API_KEY`. See `serving/README.md`.
