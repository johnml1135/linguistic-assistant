# align/

**Statistical word-gloss alignment** — a *probabilistic* source of word glosses over a verse-aligned
parallel corpus (English ↔ target), complementing the *deterministic* Apertium bidix
(`research/bilingual/`). Output = candidate `bilingual/*` sense links for a skill/human to confirm.

```
verse-aligned rows ──▶ align (THOT Eflomal | co-occurrence) ──▶ GlossTable
                   ──▶ gloss_table_to_sense_link_ops ──▶ candidate bilingual.sense_link.add ops
```

## Backends (auto-selected: THOT Eflomal → co-occurrence)
- **THOT Eflomal** (`sil-machine[thot]>=1.9`, `machine.translation.word_align_corpus(aligner="eflomal")`) —
  cross-platform (Windows/macOS/Linux, CPU, no GPU); the quality backend. This is THOT's native
  Eflomal model (`sil-thot>=3.5`, C++, Windows wheels included) — **not** the standalone POSIX-only
  `eflomal` PyPI package (source-only, no Windows build). Superseded the plain HMM aligner: same
  cross-platform footprint, better sparse-data behavior on these short low-resource verse corpora.
- **co-occurrence (Dice)** — dependency-free, deterministic; the **offline/CI** path (used by tests).

All produce symmetrized links → `build_gloss_table` → ranked target→source glosses.

## Install (uv)
```bash
cd research
uv sync --extra align         # sil-machine[thot]>=1.9 — cross-platform (Windows/macOS/Linux, CPU)
```
The dependency set is pinned in `research/uv.lock`. No torch/transformers/GPU extras. The `.venv`
for this repo is a **Windows** environment; run from PowerShell, not WSL.

## Run (offline)
```bash
python research/align/tests_smoke.py   # uses the co-occurrence backend
```

## Morpheme-level alignment over HC-parsed words (`morph_align_hc.py`)

Word alignment glosses a whole target word; but a source word often maps to a *morpheme inside* it
(`ni-na-ku-penda` = I-PRES-you-love). `morph_align_hc.py` aligns THOT over the **HC-parsed** word: it uses
the Hermit Crab analysis as the *verified* segmentation, then THOT attaches each morpheme's pivot source
token + probability, and emits a full **marker** per morpheme (form, boundary type, slot, HC gloss, source
token(s), grammatical features for affixes, confidence, agrees-with-HC).

- HC's echoed morph *forms* are corrupted, but its **gloss line is exact** — so segmentation is recovered
  by mapping each gloss back to its grammar construct (`gloss_index`), and the root surface form by
  **peeling** the known affix forms off the word. Words HC can't parse are kept whole + flagged `unparsed`.
- **THOT is required, no silent fallback** (`backend="eflomal"`, fallback disabled); `cooccur` is for tests.
- Routing: two concurring signals (THOT high-prob ∩ HC gloss) → **accept** (raise the gold affix gloss /
  root sense via a `deltas/` op); everything else **defers** — `to_deferral_records` turns the high-value
  tail into `deferrals/` tickets. Function morphemes are noisy, so it defers aggressively (precision over
  recall — never a silent wrong marker).
- Supersedes `cycle/morph_align.py`'s **greedy** segmentation with HC-verified segmentation + markers.

```bash
uv run --extra align python -m align.morph_align_hc --pair swh --backend eflomal --sample 400 [--apply]
```
Measured (swh, 400 verses): ~9k morpheme markers; TAM prefix-complexes (nime/nina/nili) surfaced.
See `align/eflomal_vs_hmm.md` for the accept-rate comparison against the retired `hmm` backend. Spec:
the OpenSpec `morpheme-alignment` change (predates the eflomal switch; describes the original
HMM-backed design).

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
