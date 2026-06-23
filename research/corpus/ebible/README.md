# datasets/ebible/

Ingest a verse-aligned **English ↔ agglutinative** New-Testament pair from the
[BibleNLP/ebible](https://github.com/BibleNLP/ebible) corpus and turn it into golden-set inputs:
tokenized parallel rows → word-gloss alignment → candidate `bilingual/*` sense links.

## Pairs set up now
All paired against **English WEB (`eng-engwebp`, public domain)**:
- **Swahili (`swh-swhulb`, Unlocked Literal Bible)** — Bantu: noun-class concord + verb-extension vowel (height) harmony.
- **Indonesian (`ind-indags`, "Bible for All")** — Austronesian: rich affix/circumfix, meN- nasal place assimilation.
- **Tagalog (`tgl-tglulb`, Unlocked Literal Bible)** — Austronesian: infixation + reduplication, voice/focus morphology.
- **Spanish (`spa-spaRV1909`, Reina-Valera 1909)** — fusional; public-domain end-to-end shakedown.

> **Why these four:** each has an open text plus a music-free single-narrator audio recording plausibly
> available for the *same* translation, so the sibling `research/audio/` add-on can later enrich them.
> Swahili's height harmony (front class `{i,e}`, back class `{u,o}`) is the closest morphological analog
> to the older vowel-harmony targets and is where the harmony-collapse machinery is aimed first. To add
> another pair, drop a verse-per-line file under `_sources/ebible/` and add its id to `config.TARGETS`.

## Pipeline

```
fetch (vref + texts) ──▶ read (verse-align, NT-only, tokenize) ──▶ align (word glosses)
                    ──▶ candidate bilingual.sense_link.add ops + manifest
```

`fetch` uses stdlib urllib (idempotent). `read` tokenizes with machine.py's `LatinWordTokenizer`
when installed, else a Unicode regex. `align` uses THOT HMM when available, else the deterministic
co-occurrence fallback (`research/align/`).

## Run

```bash
cd research
python datasets/ebible/build.py --pair swh ind tgl spa    # fetch + build all four
python datasets/ebible/build.py --pair swh --backend cooccur --no-fetch   # rebuild from cache, offline
python datasets/ebible/tests_smoke.py                     # offline, no network
```

## Outputs (under `research/golden/_sources/ebible/<eng>__<tgt>/`)
- `parallel.jsonl` — verse-aligned tokenized rows *(git-ignored; regenerable)*
- `glosses.tsv` — target word → best English gloss (prob, count)
- `sense_links.candidates.json` — candidate `bilingual/*` ops (low-confidence, skill-confirmed)
- `manifest.json` — ids, verse count, backend, license note
- `audio/` — optional add-on outputs (sample-word persistence, audio source status, review-only phone evidence, derived pronunciation / orthography reports)

Raw `*.txt` + `parallel.jsonl` are git-ignored (fetched/regenerable); the small derived gold is committed.

## How it feeds the golden set
These verse-aligned rows + candidate sense links are the **bilingual Red tests** for
`parallel-translation-qa` and the seed for building the lexicon + Hermit Crab grammar from scratch
(the sibling golden harness adds the HC `word→gloss` round-trip gate). See the `golden-pair-selection`
and `apertium-alignment-bridge` memories.

For the four targets (Swahili, Indonesian, Tagalog, Spanish), the sibling `research/audio/` add-on can optionally enrich these same
pair outputs with analyst-chosen sample words and locally supplied audio evidence. It is conservative:
no audio is assumed, and the text pipeline remains authoritative.
