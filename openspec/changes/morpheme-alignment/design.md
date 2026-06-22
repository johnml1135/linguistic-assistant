## Context

The aligner (`align/`, THOT HMM via `sil-machine`) links source tokens to target tokens. The gold grammar
(`golden/reference/hc_coverage.build_reference_model`) parses target words with Hermit Crab
(`golden/hc.run_parse`). `cycle/morph_align.py` already aligns against morphemes but segments greedily and
emits a flat table. `deltas/` is the confidence-routed write ledger; `deferrals/` turns a deferral into a
reviewable ticket. This change fuses HC (verified segmentation) with THOT (per-morpheme pivot evidence).

Guiding constraints (carried from the repo): **no silent aligner degradation** (THOT required; fail loud),
**two concurring signals to accept** (else defer — never a confident guess), and **the gold is written only
through `deltas/`**.

## Goals / Non-Goals

**Goals:**
- A verified, marker-bearing morpheme stream from HC parses (not greedy string matching).
- Per-morpheme THOT links (source token + probability), so affixes get function glosses and roots get
  context-sharpened senses.
- A full marker set per morpheme with a confidence, routed accept/defer, feeding `deltas/` + `deferrals/`.

**Non-Goals:**
- Re-training the HMM at the character level or building a new alignment model — we reuse THOT on a
  morpheme token stream.
- Forcing a segmentation on words HC cannot parse (they stay whole + flagged).
- Generating translations / MT.

## Decisions

### D1. Segmentation comes from the HC GLOSS line, mapped back to grammar constructs
HC's echoed morph *forms* are corrupted (the reindexing bug), but `gloss_seq(analysis)` is exact. Each
gloss in the analysis was produced by exactly one grammar construct — a `LexEntry` (root) or an `Affix`
(prefix/suffix/infix, with a slot). We build a `gloss → construct` index from the `LangModel` and map the
analysis's gloss line back to the ordered constructs, recovering `(form, gloss, type, slot)` per morpheme.
**Why:** this is the only reliable way to get morpheme *forms* out of HC; it is also exactly the verified
analysis we want to attach evidence to. *Alt:* trust HC's morph forms → rejected (corrupted). *Alt:*
re-segment the surface string greedily → that's `cycle/morph_align.py`, which we are improving on.

### D2. Ambiguity + unparsed handling is explicit, never silent
A word with several HC analyses uses the analysis whose gloss line matches the gold wordform analysis if
present, else the first (and records `ambiguous: true`). A word HC cannot parse becomes a single morpheme
`(form=word, gloss="?", type="word", unparsed=true)` — it still enters the stream so its *word-level*
alignment is preserved, but it is flagged so downstream never treats it as analysed.

### D3. THOT runs over a morpheme token stream; THOT is required
Each target word is expanded to its morpheme forms as separate tokens; the source side is unchanged. We
call `align(rows, backend="hmm", allow_cooccur_fallback=False)` so a missing THOT fails loudly (the
co-occurrence backend is permitted only when a caller explicitly asks, for offline tests). A per-morpheme
back-link `(verse_ref, word_idx, morph_idx)` is retained so an alignment over the flattened stream maps
back to the exact morpheme. **Why:** reuses the proven aligner unchanged; honours the no-degradation rule.

### D4. A portmanteau / null morpheme is allowed, not forced
A morpheme may align to several source tokens (portmanteau: one affix = "I"+"will") or to none (a null /
purely structural morpheme). The marker records the full set of aligned source tokens (possibly empty) with
each probability; the router treats an empty alignment as low-confidence (defer), never as a wrong gloss.

### D5. The marker set (what we carry — "as much as needed")
Per morpheme: `form`, `type` (root|prefix|suffix|infix|clitic|word), `slot` (position class), `hc_gloss`
(the grammar's stored gloss — lemma or feature label), `source_tokens` (THOT pivot links + prob),
`features` (the FsFeatStruc bundle for an affix, from the gold affix→function table), `pos` (roots),
`confidence`, and `agrees_with_hc` (does the pivot source corroborate the stored gloss?). This maps onto
LibLCM: roots → `LexEntry`/`MoStemAllomorph`, affixes → `MoInflAffMsa` (slot + features), so an accepted
marker lowers cleanly onto the gold.

### D6. Accept/defer on two concurring signals (THOT ∩ HC)
**Accept** a marker only when the THOT link is high-probability AND it agrees with the HC stored gloss
(the pivot source word is in / equals the stored gloss, or — for an affix — the pivot is the grammatical
word its function predicts). An accepted marker emits a confidence-routed `deltas/` op (raise an affix
gloss / a root sense). **Defer** everything else: the morpheme alignment is genuinely noisier than word
alignment (high-frequency function morphemes are the hard case), so disagreement or a weak link becomes a
deferral record the `deferrals/` pipeline turns into a ticket — never a silent wrong marker.

### D7. HC is the verifier of an accepted morpheme marker (optional second gate)
Before an accepted affix-gloss marker raises the gold, it MAY be round-tripped (does the gold grammar with
that affix gloss re-gloss the attested forms?) — the same propose-then-verify spine as the deferral
packages. Confirmed markers are higher-confidence; this gate is on by default for affix-function changes.

## Risks / Trade-offs

- **Function-morpheme alignment is noisy** (high-frequency, meaning-light) → the accept gate is strict and
  defers aggressively; recall is traded for precision (correct: never a wrong gloss).
- **Segmentation depends on HC coverage** → words HC can't parse are flagged `unparsed`, not force-split,
  so coverage gaps are visible, not silent.
- **Flattening loses word boundaries for THOT** → mitigated by the per-morpheme back-link and (optionally)
  a boundary sentinel token between words so the HMM doesn't align across word breaks.
- **Stored HC gloss may itself be junk** → the pivot alignment is exactly the signal that flags/corrects it
  (the same "eBible beats the gold" finding), surfaced as a deferral when they disagree.

## Migration Plan

1. Land the HC-morpheme stream builder + offline tests (mock grammar, co-occurrence backend).
2. Add the THOT-over-morphemes driver (gated on `sil-machine[thot]`).
3. Add the marker assembler + accept/defer router; wire accepted → `deltas/`, deferred → `deferrals/`.
4. Run on spa/ind/swh/tgl; record per-pair accept/defer counts + a sample of raised affix glosses.
Rollback: the module is additive; outputs are JSONL + deltas ops (reviewable, revertible); no gold impact
except through accepted, routed deltas.

## Open Questions

- Boundary sentinel between words in the THOT stream: helps the HMM not cross word boundaries, but adds a
  high-frequency token — try with and compare alignment quality.
- For an affix, "agrees with HC" needs a map from the pivot grammatical word (e.g. "you") to the feature
  (2SG.OBJ); start from a small hand table + the gold affix→function inventory, tune.
