# ParseGym — a curriculum of parsing predicaments with known good responses

ParseGym is a curated set of *scenarios* that drill the real decisions of grammar induction. Each one is
a parsing predicament drawn from data we trust (the frozen golden set + scripture), paired with a known
good response. It is the suite we use to **test small local models** (Gemma / Qwen) on the judgment that
beats pure rule-based parsing — and, importantly, to test whether they know **when not to guess**.

## What makes it different from the affix scenarios

The affix-analysis scenarios in `cycle/llm_propose.py` ask "what is this affix?" — always answerable.
ParseGym scenarios capture the messy mid-induction states and allow three kinds of correct answer:

- **`fix`** — a concrete edit, stated in LibLCM/HC mechanism terms (add a `LexEntry`; add a
  `MoStemAllomorph`; prune an `AffixTemplate` slot). The reference makes the answer knowable.
- **`unknown`** — *"I don't know."* Genuinely undecidable from the evidence at hand (a hapax with no
  gloss, an over-parse the gold can't adjudicate). Choosing this over a confident wrong guess is the win.
- **`ask_speaker`** — invoke a scripted `SpeakerQuestion` (see `questions.py`). The answer **is** choosing
  the right question and fillers. These elicitation moves are how we get past an LLM's limits on a
  language it has never seen.

## Stages (the predicament) × difficulty × phase

| Stage | The situation | Typical response |
|---|---|---|
| `cold_start` | almost nothing parses | add a root, or ask the meaning, or `unknown` |
| `hidden_rule` | an irregular stem / alternation the rules miss | add a **stem allomorph** (HC's easy path), or ask |
| `homophone` | one form, several senses/POS | ask which sense (`meaning_choice`, 3–10 options) |
| `overparse` | the grammar accepts too much | prune to the gold-POS analysis, or rank with the speaker |

`difficulty` ∈ {easy, medium, hard}; `phase` ∈ {early, late} (where in the documentation lifecycle the
question naturally arises — bootstrapping forms vs. fine distinctions on an existing grammar).

## Layout

- `schema.py` — `Scenario` + `Solution` dataclasses, the enums, JSONL read/write.
- `questions.py` — the `SpeakerQuestion` catalogue (the elicitation move-set). IDs are stable;
  scenario solutions reference them.
- `curate.py` — mines scenarios from the frozen gold + scripture and writes `gym/<pair>.jsonl`.
  `python parsegym/curate.py --pair spa --target 200` (target 100–600; grow it by raising `--target`
  and adding sources).
- `gym/<pair>.jsonl` — the curated, tracked seed sets (the gym is part of the deliverable, like the gold).

The HC-side fixes use the real mechanisms: `golden/grammar.py::LexEntry.allomorphs` →
`golden/hc.py` emits one `<Allomorph>` per stem shape (MoStemAllomorph). The harder path —
`<PhonologicalRule>` for systematic alternations — is the next layer.
