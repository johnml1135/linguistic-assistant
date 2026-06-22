# Tasks — morpheme-alignment

Tagged **[AUTO]** (deterministic) or **[GATED]** (needs `hc` CLI and/or `sil-machine[thot]`; skipped in
offline CI). The HC-morpheme stream + marker assembly are testable offline with a mock grammar + the
co-occurrence backend; the THOT path and HC round-trip are gated.

## 1. HC-morpheme stream — [AUTO]

- [x] 1.1 [AUTO] `gloss→construct` index over a `LangModel` (gloss → `LexEntry` root form / `Affix` form +
  kind + slot), handling duplicate glosses by construct preference (root over affix, then by count).
- [x] 1.2 [AUTO] `morphemes_of(word, analysis, model)`: map a HC gloss line to ordered morphemes
  `[(form, gloss, type, slot)]`; forms come from the constructs (not HC's echoed forms).
- [x] 1.3 [AUTO] Unparsed → single `word`-type morpheme flagged `unparsed`; ambiguity → prefer the
  gold-matching analysis, flag `ambiguous` (per `specs/hc-morpheme-stream`).
- [x] 1.4 [AUTO] `verse_stream(pair, verse)`: emit the per-word morpheme lists with back-links
  `(verse_ref, word_idx, morph_idx)`; an optional inter-word boundary sentinel.
- [x] 1.5 [AUTO] Offline smoke: mock `LangModel` + a canned analysis → expected marked morphemes + flags.

## 2. THOT over the morpheme stream — [GATED]

- [x] 2.1 [AUTO] Flatten the verse morpheme streams into `ParallelRow`s (src tokens ↔ morpheme-form
  tokens), keeping the morpheme back-link index alongside.
- [x] 2.2 [GATED] Drive `align(rows, backend="hmm", allow_cooccur_fallback=False)`; map the resulting
  gloss/alignment table back onto each morpheme via the back-link → `source_tokens` + probability.
- [x] 2.3 [AUTO] Portmanteau/null handling: record the full aligned-source set (possibly empty) with
  probabilities; never force 1-to-1 (per `specs/thot-morpheme-alignment`).
- [x] 2.4 [AUTO] Offline smoke (co-occurrence backend, explicitly requested): determinism + back-link round-trip.

## 3. Markers + accept/defer routing — [AUTO]+[GATED]

- [x] 3.1 [AUTO] `MorphMarker` record (form, type, slot, hc_gloss, source_tokens, features, pos,
  confidence, agrees_with_hc) + JSONL I/O; features for affixes from the gold affix→function table.
- [x] 3.2 [AUTO] `agrees_with_hc`: pivot source corroborates the stored gloss (root: token ∈ gloss;
  affix: pivot grammatical word matches the function via a small map + the gold inventory).
- [x] 3.3 [AUTO] Accept gate: high prob AND agrees → accept; else defer. Emit a confidence-routed
  `deltas/` op for accepts (affix gloss / root sense); emit a deferral record for defers.
- [ ] 3.4 [GATED] HC round-trip of an accepted affix-function marker (reuse `golden/hc.run_parse` /
  `deferrals/counterfactual`); downgrade a failing marker to a deferral (per `specs/morpheme-markers-routing`).
- [x] 3.5 [AUTO] Wire deferred markers into `deferrals/` (a morpheme deferral → a `build_ticket` record).

## 4. CLI + run — [AUTO]+[GATED]

- [x] 4.1 [AUTO] `python -m align.morph_align_hc --pair <p> [--backend hmm|cooccur] [--apply]`: run the
  pipeline, write `morph_alignments.jsonl` + a summary (counts, accepted/deferred, sample raised affixes).
- [ ] 4.2 [GATED] Run over spa/ind/swh/tgl; record per-pair accept/defer counts + sample affix glosses;
  compare affix-gloss coverage vs `cycle/morph_align.py` (greedy) on the same pairs.

## 5. Docs

- [x] 5.1 [AUTO] `align/README.md`: the HC-parsed morpheme-alignment path, the marker set, the accept/defer
  gate, the no-fallback rule, and how it relates to (supersedes the segmentation of) `cycle/morph_align.py`.
- [x] 5.2 [AUTO] Update memory: morpheme-alignment = HC verified segmentation + THOT per-morpheme markers,
  accept/defer → deltas/deferrals; where it plugs into hc.py / align / deltas / deferrals.
