## Why

THOT/HMM alignment today links whole **target words** to source words. But the vernacular languages are
morphologically rich: one source word (`you`, `will`, `I`) maps to a *morpheme inside* a target word
(`ni-na-ku-penda` = I-PRES-you-love). So an affix never gets its own gloss, and a polysemous root is only
ever glossed to its lemma. `cycle/morph_align.py` already re-aligns against morphemes, but it segments by a
**greedy string match** against the induced model — unverified, and it emits only a flat morpheme→gloss
table with no provenance.

We can do better by aligning THOT over the **HC-parsed** word. Hermit Crab gives a *verified* analysis of
each word (which lexeme + which affixes, in order); THOT then attaches, per morpheme, the **pivot source
token + an alignment probability**, and we carry a full **marker** set (boundary type, slot, gloss,
grammatical function/features, confidence, agrees-with-HC). The result is morpheme-grounded evidence that
raises affix glosses and sharpens root senses, routes through the same accept/defer gate, and feeds the
deltas ledger + the deferral-ticket pipeline — never a silent wrong marker.

Note: HC's echoed morph *forms* are corrupted by a known reindexing bug, but its **gloss line is exact**;
so the segmentation is recovered by mapping each gloss in the analysis back to the grammar construct that
produced it (lexeme form / affix form + kind + slot), which is reliable.

## What Changes

- A **HC-morpheme stream**: parse each target word with the gold grammar, map the (reliable) gloss line
  back to its grammar constructs, and emit an ordered, marked morpheme list `[(form, gloss, type, slot)]`
  per word, with a back-link to `(verse, word_idx, morph_idx)`. Words HC cannot parse are kept whole and
  flagged `unparsed` — honest, never force-segmented.
- **THOT over the morpheme stream**: replace each word with its morphemes as tokens and align the source
  against that stream, producing a per-morpheme `(source_token, probability)` link. **THOT is required —
  no silent co-occurrence fallback** (consistent with the existing no-degradation rule); the offline
  co-occurrence backend is allowed only when explicitly requested for tests.
- **Per-morpheme markers + accept/defer routing**: assemble the marker set (boundary type, slot, gloss,
  pivot source token, grammatical function/features for affixes, alignment confidence, agrees-with-HC) and
  route: two concurring signals (THOT high-prob ∩ HC gloss agreement) → **accept** (raise the gold affix
  gloss / root sense via a confidence-routed `deltas/` op); otherwise → **defer** (emit a deferral record
  the existing ticket pipeline turns into a package). Never emit a confident marker on one weak signal.
- A CLI to run the morpheme alignment for a pair and write `morph_alignments.jsonl` + a summary.

## Capabilities

### New Capabilities
- `hc-morpheme-stream`: turn a verse's words into a verified, marked HC-parsed morpheme stream (gloss line
  → grammar constructs → ordered `(form, gloss, type, slot)`), unparsed words kept whole + flagged, with
  back-links to `(verse, word, morph)`.
- `thot-morpheme-alignment`: run THOT over the morpheme stream ↔ source and produce per-morpheme
  `(source_token, probability)` links; THOT required, no silent fallback; deterministic given inputs.
- `morpheme-markers-routing`: assemble the per-morpheme marker set and route accept (raise the gold via
  `deltas/`) / defer (→ a deferral record), with a confidence on every marker; never a silent wrong marker.

## Impact

- **New code** under `research/align/` (or `research/morphalign/`): the HC-morpheme stream builder, the
  THOT-over-morphemes driver, the marker assembler + router, and a CLI.
- **Reuses (no breaking changes)**: `golden/hc.py` (`run_parse` + `gloss_seq`), `golden/reference/
  hc_coverage.py` (`build_reference_model` — the gold grammar as a `LangModel`), `align/` (THOT HMM,
  `allow_cooccur_fallback=False`), the gold affix→function table (`grammar_rules.jsonl`), `deltas/` (the
  write-back ledger), and `deferrals/` (a deferred morpheme marker becomes a resolution ticket).
- **Supersedes** `cycle/morph_align.py`'s greedy segmentation with HC-verified segmentation (the cycle
  module stays as the offline/co-occurrence quick path; the new module is the verified, marker-bearing one).
- **No change** to the frozen golden sets except via accepted markers through the `deltas/` path.
- **Validation**: offline smoke tests (mock grammar + co-occurrence backend); HC/THOT-gated tests when the
  `hc` CLI and `sil-machine[thot]` are present.
