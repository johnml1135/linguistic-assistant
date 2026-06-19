# golden_sets/ — the FROZEN evaluation target

This is the **golden set**: the pristine, online-verified references the system is scored against. It is
**committed and read-only by convention** — the hill-climber must never write here. Separation of
concerns:

| Tier | Location | Tracked? | Who writes it |
|---|---|---|---|
| **Golden set** (frozen target) | `golden_sets/<pair>/` | **yes** | `golden/reference/compile.py` (deliberate, reviewed regenerate) |
| Raw downloads + compile cache | `golden/_sources/reference/` | no (gitignored) | the fetchers (regenerable) |
| Working copy (hill-climber) | `cycle/out/`, `deltas/store/`* | out: no · store: yes | the cycle / accumulate / propose loop |

\* `deltas/store/` is the *proposal ledger* (the product), tracked separately; it is not the gold.

So "reproduce the gold" (hill-climbing in `cycle/out/`) and "score against the gold"
(`golden/reference/evaluate.py` reads `golden_sets/`) can never contaminate each other.

## Contents per `<pair>/`
- `golden_set.json` — POS (LibLCM `PartOfSpeech`, 3-way voted), affix→function gold (`morph_type` +
  inflection `FsFeatStruc`), bilingual glosses (Wiktionary), key terms, stats.
- `golden_lexicon.txt` — the full real-word list ("more words than scripture").
- `golden_scripture.tsv` — the scripture-attested validation slice (word → POS, gloss, source flags).

Regenerate deliberately with `python golden/reference/compile.py --pair <p>` (re-fetches into the cache,
re-freezes here). Treat a change to these files as a reviewed gold update, not incidental churn.
