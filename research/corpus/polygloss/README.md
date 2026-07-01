# corpus/polygloss/

Ingest the [PolyGloss corpus](https://huggingface.co/datasets/lecslab/polygloss-corpus)
(353,266 hand-annotated interlinear-glossed examples, 2,077 languages) as a **blind benchmark for
our own HC-grammar-induction pipeline** — see `../../Polygloss_integration.md` for the full plan,
rationale, and what's still pending. This package is the adapter layer only; `align/`, `engine/`,
and `gold/goldio.py` are reused unmodified.

## Files

| File | Role |
|---|---|
| `schema.py` | `PolyglossRow` — the corpus's row schema (stdlib only, no `datasets` import). |
| `convert.py` | Row → `engine/igt.py::MorphWord` list; the Leipzig all-caps grammatical/lexical split; row → `align/contract.py::ParallelRow`; the English-metalanguage filter. |
| `to_gold.py` | Held-out rows → `wordforms.jsonl`/`lexicon.jsonl` records, written via `gold/goldio.py::write_gold()`. |
| `score.py` | Parse/lemma/feature-recall scoring, adapted from `gold/hc_validate.py` (that module is eBible-scripture-coupled; this one isn't — see the plan doc §4.1/§4.3). |
| `fetch.py` | Pull a language's rows from the (gated) HF dataset and cache them as JSONL. |
| `tests_smoke.py` | Offline tests against a hand-built fixture row — no network, no `hc` CLI. |

## Run it

```bash
cd research
uv sync --extra polygloss           # installs `datasets`
python corpus/polygloss/tests_smoke.py   # offline, no network — should print "8 tests passed"

# real fetch needs HF auth + accepting the dataset's access agreement first:
huggingface-cli login
python -c "from corpus.polygloss.fetch import fetch_language; print(fetch_language('vera1241'))"
```

## Status

Fetch → convert → gold → score is built and offline-tested end to end. Feeding a picked language
into `induce/tdd.py` (grammar induction proper) still needs the small path adapter described in the
plan doc's §4.3 — `tdd.py`'s frequency/gloss loaders are hardcoded to the eBible corpus layout, so
this isn't a drop-in call yet. See `../../Polygloss_integration.md` §6 for the current build order.
