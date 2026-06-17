# `golden/` — self-validating lexicon + morphology golden sets

Manually-constructed-but-**machine-verified** gold for the lexeme-proposal task, plus an
ablation harness that turns it into scored agent-proposal instances. Design:
[../../docs/superpowers/specs/2026-06-16-golden-set-design.md](../../docs/superpowers/specs/2026-06-16-golden-set-design.md);
build order + status: [PLAN.md](PLAN.md).

## The four artifacts (per language, e.g. `golden/lez/`)

- `raw/igt.jsonl` — surface + free translation only (what the agent/linguist sees).
- `gold/lexicon.lift` — verified lexicon (LIFT, FLEx-importable).
- `gold/grammar.hcgr.xml` — verified morphology (HermitCrab grammar).
- `gold/analyses.jsonl` — per-wordform gold gloss line (the oracle).
- `meta.json` — provenance, **license**, counts, and the HC round-trip coverage that *is*
  the certification (no human in the loop).

## How verification works (no human)

The binding certifier is **deterministic**: HermitCrab re-parses each gold wordform and must
reproduce its **gold gloss line**. (HC's echoed morph *forms* are corrupted by a segment
-reindexing bug, so we score the reliable Gloss line — which is also exactly the
agent-proposal reward.) Forms are transliterated to digit tokens because HC mangles
non-ASCII output; see `hc.Translit`.

## Public interface (for harness / RAG / RL callers)

```python
from golden import igt, grammar, ablate, score

recs  = igt.parse_file(".../lez-train-track2-uncovered")
words = list(igt.iter_words(recs))
model = grammar.build_model("lez", words)          # candidate lexicon + affixes

inst  = ablate.ablate_lex(model, words, rank=3)    # remove a morpheme -> instance
# inst.incomplete  : crippled LangModel given to the agent
# inst.held_out    : [(underlying_form, gold_analysis), ...] the agent must restore
# inst.answer_key(): what was removed (for offline analysis only)

prop  = score.Proposal(lex=[grammar.LexEntry(form="за", gloss="1sg.ERG")], affix=[])
rew   = score.score(inst, prop)                    # pure (instance, proposal) -> Reward
# rew.reward in [0,1]: held-out gloss recall after repair, 0 if it regresses the control set
```

`score.score` is the deterministic reward function for both harness eval and RL. Build a
fresh gold with `python -m golden.build --lang <code> --igt <file> --out golden/<code>`.

## Status

Lezgi (`lez`) built: **97.8% gloss round-trip** over 1,897 wordforms, fully automated.
Next: Tsez, Uspanteko; Gitksan as a low-resource stress case. Tier-2 (phonological rules,
real-FLEx `.fwdata` ingestion) deferred per the spec.

## Verifier dependency

`hc` CLI from `sil.machine.hcparser` (.NET, run with `DOTNET_ROLL_FORWARD=LatestMajor`).
`golden/_sources/` (SIGMORPHON 2023, **CC BY-NC 4.0**) is git-ignored — rebuild gold from it.
