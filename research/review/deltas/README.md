# deltas/ — the controllable delta store

The **source of truth** for proposed LibLCM edits: the cycle/LLM emit change-set ops, this store
accumulates them across runs, routes each by confidence, and persists a committable JSONL. Appliers
(MiniLcm/Harmony, FLExTools/flexlibs) consume the **accepted** set — the store never touches FieldWorks.

```
cycle model + LLM scenarios + glosses ──emit.py──▶ change-set ops (+confidence, +provenance)
   ──store.add (idempotent by op_signature)──▶ deltas/store/<pair>.deltas.jsonl
   ──store.route──▶ accepted (auto) | review (human / LLM second-guess) | deferred
```

## Why a delta store (not write to FLEx directly)
- **Controllable + addable** — every proposal is a diffable, git-tracked op with confidence + provenance
  + status; you can review, second-guess (`divide-senses`: "these two are one word"), accept, or reject.
- **Accumulates** — running the cycle many times merges by signature; `rounds_seen` and max-confidence
  record reinforcement. Nothing is lost or duplicated.
- **Backend-agnostic** — the same accepted ops apply to MiniLcm/Harmony (lexicon, syncable, no FieldWorks)
  or into a real FLEx project via a FLExTools module / flexlibs (Windows). Direct `.fwdata` writes are
  avoided precisely because they lose this control layer (the "silent-skip" risk).

## Confidence routing
Each op carries a composed confidence (frequency, alignment prob, LLM/heuristic analysis, HC gate). The
store routes: `≥0.85` → **accepted** (auto-apply), `0.5–0.85` → **review** (human or LLM), `<0.5` →
**deferred**. A human/LLM `decision(accept|reject)` is **locked** and never auto-rerouted. Thresholds are
tunable per run. This is the [[guess-ask-or-defer]] skill as a pipeline stage.

## Accumulate, then apply
```bash
cd research
python cycle/accumulate.py --pair spa --rounds 12 --seconds 120   # keep iterating (resume each round,
                                                                  # emit deltas, stop loop-until-dry)
python deltas/build_store.py --pair spa --round 1                 # (or emit a single round manually)
python deltas/apply.py       --pair spa                           # accepted lexical ops → MiniLcm JSON
python deltas/tests_smoke.py                                      # offline tests
```
`accumulate.py` drives the cycle round over round (each resumes from the prior `out/<pair>_model.json`,
so roots/affixes/glosses/POS grow) and folds each round's deltas into this store — verified on spa:
roots 608→938, coverage 0.89→0.96, store 1879→2313 over 3 rounds. `apply.py` exports the **accepted**
`lexical.*` ops to a MiniLcm-shaped lexicon JSON (Harmony/LexBox/FwLite import); `morphophonology.*` ops
stay as git grammar deltas; `apply_via_flexlibs` is the documented Windows/FieldWorks bridge into a real
FLEx project.
Ops follow `proposal.change_set` (validated): `lexical.*` (MiniLcm-shaped), `morphophonology.*` (HC),
`bilingual.*`. The accepted set is a validated `ChangeSet` (`store.accepted_change_set()`).
