# align/

**Statistical word-gloss alignment** — a *probabilistic* source of word glosses over a verse-aligned
parallel corpus (English ↔ target), complementing the *deterministic* Apertium bidix
(`research/bilingual/`). Output = candidate `bilingual/*` sense links for a skill/human to confirm.

```
verse-aligned rows ──▶ align (THOT HMM | co-occurrence) ──▶ GlossTable
                   ──▶ gloss_table_to_sense_link_ops ──▶ candidate bilingual.sense_link.add ops
```

## Backends (auto-selected: THOT HMM → co-occurrence)
- **THOT HMM** (`sil-machine[thot]`, `machine.translation.word_align_corpus(aligner="hmm")`) —
  cross-platform (Windows/macOS/Linux, CPU, no GPU); the quality backend.
- **co-occurrence (Dice)** — dependency-free, deterministic; the **offline/CI** path (used by tests).

All produce symmetrized links → `build_gloss_table` → ranked target→source glosses.

## Install (uv)
```bash
cd research
uv sync --extra align         # sil-machine[thot] — cross-platform (Windows/macOS/Linux, CPU)
```
The dependency set is pinned in `research/uv.lock`. No torch/transformers/GPU extras. The `.venv`
for this repo is a **Windows** environment; run from PowerShell, not WSL.

## Run (offline)
```bash
python research/align/tests_smoke.py   # uses the co-occurrence backend
```

## How it fits
- It's the **statistical** half of word-gloss discovery; the Apertium bidix is the **symbolic** half.
  Both emit candidate `bilingual/*` sense links (validated by `research/proposal/change_set.py`).
- Candidates are **low-confidence by construction** (capped ≤0.6, provenance recorded) — a skill /
  human confirms before commit. The deterministic HC golden gate still decides what lands.

## Golden-set build flow (eBible → gold)
1. Fetch a verse-aligned pair from the **eBible** corpus (English WEB ↔ an agglutinative target).
2. Tokenize; **align** (this package) → candidate glosses → seed the lexicon + bidix sense links.
3. Discover morphology; **build Hermit Crab from scratch**; gate on the `word→gloss` golden set.
4. The parallel side feeds `parallel-translation-qa`'s missing-concept / agreement checks.

See the language-pair assessment in the `golden-pair-selection` memory and `research/bilingual/`.
