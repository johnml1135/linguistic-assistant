# datasets/ebible/

Ingest a verse-aligned **English ↔ agglutinative** New-Testament pair from the
[BibleNLP/ebible](https://github.com/BibleNLP/ebible) corpus and turn it into golden-set inputs:
tokenized parallel rows → word-gloss alignment → candidate `bilingual/*` sense links.

## Pairs set up now
- **English WEB (`eng-eng_web`, public domain) ↔ Turkish (`tur-turytc`)** — agglutinative, vowel harmony.
- **English WEB ↔ Hungarian (`hun-hun`)** — Uralic, heavy agglutination + vowel harmony.

> **Finnish note:** Finnish is **not** in the redistributable eBible `corpus/` (the copyright holder
> didn't permit redistribution, so BibleNLP excludes it). **Hungarian** is the closest available
> stand-in (also Uralic/agglutinative). To add Finnish, drop a Finnish verse-per-line file under
> `_sources/ebible/` from another source and add its id to `config.TARGETS`.

## Pipeline

```
fetch (vref + texts) ──▶ read (verse-align, NT-only, tokenize) ──▶ align (word glosses)
                    ──▶ candidate bilingual.sense_link.add ops + manifest
```

`fetch` uses stdlib urllib (idempotent). `read` tokenizes with machine.py's `LatinWordTokenizer`
when installed, else a Unicode regex. `align` uses eflomal/THOT when available, else the deterministic
co-occurrence fallback (`research/align/`).

## Run

```bash
cd research
python datasets/ebible/build.py --pair tur hun            # fetch + build both
python datasets/ebible/build.py --pair tur --backend cooccur --no-fetch   # rebuild from cache, offline
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

For Turkish and Hungarian only, the sibling `research/audio/` add-on can optionally enrich these same
pair outputs with analyst-chosen sample words and locally supplied audio evidence. It is conservative:
no audio is assumed, and the text pipeline remains authoritative.
