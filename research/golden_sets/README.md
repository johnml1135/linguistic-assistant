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

## Contents per `<pair>/` — a true generative lexicon + grammar (not a flat word list)
- `lexicon.jsonl` — one entry **per LEMMA**: `{word, pos, senses (REAL only), homograph, in_scripture,
  inflection_class, irregular}`. Inflected forms are NOT here — they are generated. One `LexEntry` per
  lexeme; `inflection_class` ties it to a rule table; `irregular` lists the override cells (e.g. `abrir`'s
  participle `abierto`).
- `lexicon.lift` — the same lexicon as **FLEx-native LIFT XML**, directly importable into FieldWorks.
- `inflection_classes.jsonl` — **the generative rules**: each class = `{class_id, pos, size, rules:
  [{features, kind, remove, add}]}`. Spanish induces 3 verb classes (the -ar/-er/-ir conjugations).
  This is what we want the LLM/hill-climber to *find* — the transforms, not the surface forms.
- `wordforms.jsonl` — **the TEST ORACLE** (derivable from lemma + class + overrides): `{surface, lemma,
  pos, features, source}`. We don't author these; the grammar must *reproduce* them.
- `grammar_rules.jsonl` — flat affix→function inventory (feeds the HC grammar build).
- `phonology.jsonl` — segment inventory + natural classes + phonological rules (`status` active/staged).
- `key_terms.jsonl` / `meta.json` / `golden_scripture.tsv` (a wordform view: surface → lemma + analysis).
- `alignment_glosses.jsonl` — words resolved from the parallel corpus, not Wiktionary (proper-noun names
  + leftover content words): `{forms, best, candidates[top5], confidence}`. Confident ones are folded into
  the lexicon (`gloss_source: "alignment"`) by `align_gloss.py` as compile's final pass.

Load in code with `golden/reference/goldio.py::load_gold(pair)`. The lexeme/wordform split mirrors LibLCM:
a wordform's meaning comes from its lemma entry + its feature bundle, not a per-form gloss.

## HC-validated by analysis recall
`python golden/reference/hc_validate.py --pair <p> [--grammar lemma|class]` builds an HC grammar and
scores **lemma recall** against `wordforms.jsonl` (does HC parse each scripture wordform to the *right*
lemma?). Two grammars:
- `--grammar lemma` (memorised): lemmas-as-roots + UniMorph forms as allomorphs. spa 0.97 / ind 1.0.
- `--grammar class` (**generative + class-restricted**): induced **stems** as roots + the inflection-class
  affixes, with each class encoded as a POS so an `-ar` suffix can't attach to an `-ir` stem; forms the
  rules can't generate (suppletion, derivation) are stem allomorphs. **spa 1.0 / ind 1.0** — better than
  memorising every form, while staying generative for the regular paradigm.

Phonological rules (the harder path) are emitted by the production builder
(`golden/hc.py::build_grammar_xml(phon_rules=…)`, verified loadable). At biblical-domain scale spa/ind
recall is already saturated by class-splits + allomorphy, so no language rule is activated yet; the next
real one — Indonesian meN- nasal place-assimilation — needs consonant place features in the inventory.

Regenerate deliberately with `python golden/reference/compile.py --pair <p>` (re-fetches into the cache,
re-freezes here). Treat a change to these files as a reviewed gold update, not incidental churn.
