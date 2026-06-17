# `golden/` — HermitCrab grammar model + virtuous-cycle harness (origin-agnostic)

The reusable morphology engine + improvement loop. **It does not own where the gold comes
from.** The gold origin is now eBible parallel text + statistical word glosses (eflomal) +
FieldWorks data (see the `golden-pair-selection` work) — the SIGMORPHON-IGT golden set that
used to live here, its built lexicons, and its parser were removed.

## What an ingester must produce
A list of `igt.MorphWord` — a surface form + ordered `(form, gloss)` morphs. That's the only
contract; everything below is independent of the source.

## Modules
- `igt.py` — the `Morph`/`MorphWord` interchange types (no parser).
- `grammar.py` — `LangModel`, `LexEntry`, `Affix`, and `build_model`: Leipzig casing split
  (lowercase gloss → lexical root; UPPERCASE → grammatical affix) + **affix-template /
  position-class slot** inference (`MoInflAffixTemplate`/`Slot`, multi-slot membership).
- `hc.py` — emits a HermitCrab grammar (`build_grammar_xml`, the ordered-slot affix template)
  and drives the `hc` CLI (`run_parse`, `round_trip`, gloss-line scoring, `Translit`). Works
  around two HermitCrab.NET output bugs (non-ASCII corruption; morph-form reindexing).
- `ablate.py` / `score.py` — the **virtuous cycle**: remove a morpheme → instance; pure
  `(instance, proposal) → reward` via HC re-parse gated on non-regression.
- `scorer.py` / `instances.py` — the seam consumed by `research/eval` (`build_scorer`,
  `make_instances`) and `research/assess` (`LangModel` + `hc`).
- `lift_emit.py` — LIFT lexicon emitter (FLEx-importable).

## Verifier dependency
`hc` CLI from `sil.machine.hcparser` (.NET; run with `DOTNET_ROLL_FORWARD=LatestMajor`).

## Status
Engine + harness intact and origin-agnostic. The freeze/ingest pipeline for the new origin
(eBible/eflomal/FieldWorks → `MorphWord`s → frozen per-language gold) is the next piece;
once it populates `golden/<glottocode>/`, `research/eval` and `research/assess` run against it
unchanged.
