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

## Contents per `<pair>/` — reviewable JSONL (one record per line; `grep`- and diff-friendly)
- `lexicon.jsonl` — one record per word: `{word, pos, gloss, is_lemma, in_scripture}` (sparse — null
  fields omitted). The full real-word list, the "more words than scripture" layer. Large; the bulk data.
- `grammar_rules.jsonl` — the affix→function rules: `{affix, morph_type, features, inflection (FsFeatStruc),
  count}`. **The main human-review target.**
- `senses.jsonl` — sense inventory for scripture-attested words: `{word, pos[], senses[], homograph}`.
- `phonology.jsonl` — segment inventory + natural classes + phonological rules (rules carry a `status`:
  `active` = emitted into HC; `staged` = described, not yet emitted).
- `key_terms.jsonl` — `{term}` (unfoldingWord key terms).
- `meta.json` — a single summary object: pair, sources, stats, destination, conflict/uncovered samples.
- `golden_scripture.tsv` — the scripture-attested validation slice (tabular: word → POS, gloss, flags).

Load in code with `golden/reference/goldio.py::load_gold(pair)` (reconstructs the in-memory dict).

## HC-validated
`python golden/reference/hc_validate.py --pair <p>` builds an HC grammar from this gold (roots +
allomorphs + grammar_rules + the phonology feature substrate) and confirms Hermit Crab **loads it cleanly
and parses the golden entries** (spa 0.995 compositional → 1.0 with `--close`; ind 1.0).

Regenerate deliberately with `python golden/reference/compile.py --pair <p>` (re-fetches into the cache,
re-freezes here). Treat a change to these files as a reviewed gold update, not incidental churn.
