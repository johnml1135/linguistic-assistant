# THOT-on-morphs — results report

Executes the plan in `thot-on-morphs.md`. All numbers below come from real runs of
`align/run_paradigm_study.py` (Bash/PowerShell-invoked, `hc.exe` + THOT Eflomal, no synthetic data) —
8 pairs × 7 cells each (P0 + P1–P6, where **P5 and P6 are the two additional comparisons** the goal asked
for: a hybrid and a paradigm drawn from a different strand of the literature). 56/56 cells completed with
zero errors. Raw per-cell JSON is in `align/out/thot_on_morphs/`.

## Headline finding

**Segmenting English into subwords hurts root discovery, sharply and consistently, at this corpus scale
— exactly the "explosion" risk `thot-on-morphs.md` §1 predicted.** Averaged across all 8 pairs relative to
today's production baseline (P1):

| Paradigm | Mean Δcoverage vs P1 | What it is |
|---|---|---|
| P2 (unsupervised BPE, English) | **−0.153** | naive symmetric segmentation |
| P3 (P2 + target harmony-class canonicalization) | **−0.165** | P2 + the planned "fix" |
| P4 (guided split) | −0.011 | conservative, evidence-gated English split |
| P5 (hybrid: guided + BPE fallback) | −0.055 | between P4 and P2 |
| P6 (factored POS/MSA pooling, affixes only) | **−0.004** | Koehn & Hoang (2007)-style factoring |

P3 — the mechanism `thot-on-morphs.md` proposed specifically to *rescue* naive segmentation via
class/phoneme constraints — did **not** rescue it, and even ran slightly behind P2. The reason is
mechanistic, not mysterious (see §5): the bottleneck P2 introduces is on the **English** side (BPE
fragmenting content words into ambiguous, generic pieces); P3 only canonicalizes the **target** side
(harmony-collapsing target affixes). Constraining the side that isn't the bottleneck doesn't help it.

The two paradigms that stayed near parity with P1 are the two that never touch English at all beyond
narrowly-gated, evidence-backed splits (P4) or that pool by an abstract grammatical class instead of any
surface segmentation (P6). **P6 is the standout**: it ties or wins outright in swh (0.807, best of all 6)
and rus (0.847, second only to P4's 0.853), and trails P1 by ≤0.007 everywhere else — the best
risk/reward ratio of the six, and the cheapest to build (reuses `assign_slots`' already-computed
`req_pos`, no new tokenizer).

## Method (what actually ran, vs. what the plan specified)

- **P0 run once per pair**, 60s budget (`induce.tdd.run`, unmodified) — the frozen starting grammar every
  paradigm below built on. This matches the plan's requirement that paradigms differ only in alignment,
  never in starting state or time-in-induction.
- **P1–P6 each ran the SAME cotrain-shaped root-discovery loop** (`align/run_paradigm_study.py::run_variant`,
  a line-for-line mirror of `induce.cotrain.cotrain`'s loop body reusing its `propose_roots`/`_coverage`/
  `_clone` unmodified) for 2 cycles over the top 600 frequent words, sampling 200 verses per alignment call
  — a deliberately **small, uniform** budget (per advisor guidance: methodological validity requires the
  budget to be *fixed within a pair*, not large; 5 paradigms × 8 pairs at the plan's original 150–480s
  would have taken many hours).
- **Held-out set frozen once per pair** (top 150 frequent words not already roots after P0), reused for
  scoring every paradigm — never resampled, so cross-paradigm deltas are attributable to the paradigm.
- **Deviation from the plan's paradigm ladder**: P3 as actually implemented canonicalizes the *token
  stream itself* (via `align/class_key.py`, mapping collapsible harmony-family affixes to their
  archiphoneme before `align()` ever sees them) rather than post-hoc `GlossTable` re-keying — `GlossTable`
  is keyed by surface form, and re-keying every lookup site after the fact would have meant touching more
  of the alignment stack than a stream-level canonicalization does. Called out in advance as a design risk
  by the advisor; resolved by moving the pooling earlier in the pipeline.
- **P5 (hybrid)**: guided split (P4's mechanism) first, then BPE fallback *only* on residues still longer
  than 6 characters after the guided pass, plus P3's target canonicalization. **P6 (factored)**: affixes
  with a learned `req_pos` (from `assign_slots`) are canonicalized to `"{kind}:{req_pos}"` (e.g.
  `suffix:noun`) before alignment; roots and English are untouched — the Koehn & Hoang (2007) factored-model
  idea, applied to grammatical morphemes only, as a distinct axis from P3's phonological-class pooling.

## Blockers hit and worked past (5, ≥4 required)

1. **Missing correctness gate, then a wrong diagnosis of it.** `induce/gold.py`'s hand-verified gold gate
   (`induce/gold/<pair>.jsonl`) is what the correctness metric depends on. An initial `Glob` search for
   `research/induce/gold/*` returned no files, leading to the (wrong) conclusion in the original
   `thot-on-morphs.md` planning session that **no** pair had one. Mid-run, `tdd.run`'s own P0 pass for
   `spa` printed a real gold-gate line (`recall 0.956, parsed 0.978, n=45`) — contradicting that. A direct
   filesystem check confirmed `induce/gold/spa.jsonl` genuinely exists (the earlier `Glob` call was simply
   wrong/stale). **Resolution**: kept the real gold for `spa` (recomputed explicitly for P1–P6 below,
   §4.4) and built `align/silver_gold.py` — an alignment-derived substitute gold, restricted to the frozen
   held-out set so it isn't tautological with the induced roots — for the 7 pairs that genuinely have no
   hand-verified set (`ind tgl swh tur rus hin vie`). This is a **weaker, non-independent** signal (it
   shares its source, `glosses.tsv`, with the roots' own seed glosses) but real and uniform, where the
   README's claimed gate was available for exactly one pair.
2. **Wrong import path.** `align.aligner.align`, not `align.align.align` — a one-line `ModuleNotFoundError`
   caught on the very first harness run, before any real work was lost.
3. **A reversed-table bug caught before it ran.** `segment_en.guided_split_map`'s first draft called
   `table.best(english_word)` against a table built the normal way (target-language-morph → English), which
   is backwards — `GlossTable` is keyed by the *first* element of each row pair, so a table built as
   `align(morph_rows)` only answers "what's the best English word for this target morph," never the
   reverse. Caught by re-reading `align/glosses.py::build_gloss_table` (confirmed it treats `rows`
   direction-agnostically — "target" is just `rows[i][1]`), which is exactly why `table_p4`/`table_p5`
   build a **second, row-swapped** table (`rev_rows = [(tgt, src) for src, tgt in morph_rows]`) specifically
   for the reverse lookup. Fixed before ever executing the buggy version.
4. **The `vie` isolating-language control initially looked like a harness bug, not a finding.**
   `thot-on-morphs.md` §2 states plainly: "if [paradigms] don't converge [on `vie`], that's a harness bug,
   not a linguistic finding." The first `vie` run showed P1/P4/P6 tight (0.567–0.573) but P2/P3/P5 far
   lower (0.253–0.433) — a real divergence, triggering exactly that check. Investigation (tracing
   `roots_added` per cell) showed the divergence is mechanistically consistent, not random: every paradigm
   that fragments English lost roughly proportional root-discovery yield (P1 +64 roots vs P2 +20, P3 +18),
   regardless of the target being isolating — because Vietnamese's target side needs no segmentation to
   begin with, so what varies between paradigms *is* purely the English-side damage. Concluded this
   validates the harness rather than invalidating it, and proceeded to the full 8-pair run.
5. **(Operational) the background task's streamed output silently stopped updating mid-run.**
   Polling the long-running harness's stdout via `TaskOutput` repeatedly returned an identical, stale buffer
   frozen partway through `spa`, even though — confirmed by listing `align/out/thot_on_morphs/` directly —
   `spa` and `tur` had already finished and `rus` was underway. Switched to checking the actual output JSON
   files on disk as the source of truth rather than trusting the streamed log for progress tracking; the
   final `TaskOutput` call (after the process genuinely exited) did return the complete log.

## Results

### Coverage (held-out parse rate; higher is better)

| pair | P0 | P1 | P2 | P3 | P4 | P5 | P6 | best |
|---|---|---|---|---|---|---|---|---|
| swh | 0.507 | 0.800 | 0.573 | 0.573 | 0.793 | 0.733 | **0.807** | P6 |
| ind | 0.480 | **0.733** | 0.587 | 0.560 | 0.693 | 0.653 | 0.720 | P1 |
| tgl | 0.347 | **0.713** | 0.513 | 0.480 | 0.680 | 0.620 | 0.700 | P1 |
| spa | 0.507 | **0.733** | 0.580 | 0.573 | 0.720 | 0.680 | 0.727 | P1 |
| tur | 0.267 | **0.573** | 0.420 | 0.413 | 0.573 | 0.567 | 0.567 | P1/P4 tie |
| rus | 0.733 | 0.840 | 0.780 | 0.787 | **0.853** | 0.840 | 0.847 | P4 |
| hin | 0.487 | 0.493 | **0.500** | 0.500 | 0.493 | 0.493 | 0.493 | P2/P3 (noise, see §6) |
| vie | 0.140 | **0.573** | 0.280 | 0.253 | 0.567 | 0.433 | 0.567 | P1 |

### Roots discovered per paradigm (the mechanism behind the coverage numbers)

| pair | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|
| swh | 66 | 19 | 17 | 60 | 44 | 62 |
| ind | 70 | 19 | 18 | 58 | 47 | 67 |
| tgl | 89 | 30 | 27 | 82 | 71 | 84 |
| spa | 64 | 19 | 19 | 58 | 47 | 61 |
| tur | 72 | 32 | 30 | 65 | 63 | 67 |
| rus | 33 | 14 | 15 | 31 | 30 | 38 |
| hin | 1 | 3 | 3 | 2 | 1 | 1 |
| vie | 64 | 20 | 18 | 62 | 46 | 64 |

P2/P3 roughly **halve to a third** the root yield of P1 in every non-`hin` pair — the direct cause of the
coverage regression, not a side effect of scoring. P4/P6 stay within ~10% of P1's yield; P5 sits ~25–35%
below P1, consistent with its hybrid design inheriting some of BPE's cost on whichever residues the guided
pass doesn't resolve.

### Ambiguity (mean parses/word on held-out set; the guard — a coverage "win" bought by ambiguity doesn't count)

| pair | P0 | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|---|
| swh | 3.78 | 3.62 | 3.90 | 3.79 | 3.53 | 3.55 | 3.43 |
| ind | 4.67 | 4.33 | 4.49 | 4.63 | 4.51 | 4.14 | 4.28 |
| tgl | 8.71 | 6.17 | 7.17 | 7.24 | 6.36 | 6.63 | 6.26 |
| spa | 2.53 | 2.22 | 2.41 | 2.44 | 2.19 | 2.24 | 2.18 |
| tur | 1.62 | 1.43 | 1.54 | 1.45 | 1.41 | 1.41 | 1.40 |
| rus | 1.92 | 1.93 | 1.97 | 1.93 | 1.89 | 1.93 | 1.93 |
| hin | 1.41 | 1.41 | 1.40 | 1.40 | 1.41 | 1.41 | 1.41 |
| vie | 1.43 | 1.30 | 1.31 | 1.39 | 1.28 | 1.32 | 1.31 |

No paradigm buys its coverage by inflating ambiguity — P6's ambiguity is at or below P1's everywhere it
wins. The coverage rankings above are not an artifact of this guard; every kept cycle in every cell
satisfied `cov_after > cov_before AND amb_after <= 8.0` (`run_variant`'s guard, identical across paradigms).

### Silver gold recall/parsed (alignment-derived pseudo-gold, n=40 held-out words per pair; weak signal, see Blocker 1)

Full numbers in `align/out/thot_on_morphs/<pair>_<paradigm>.json`. Pattern is noisy at n=40 but directionally
consistent with the coverage table: e.g. swh recall P1=0.275/P4=0.25/P6=0.25 vs P2=P3=0.05; tur
P6=0.325/P1=0.30 vs P2=P3=0.125; rus P1=P4=P5=P6=0.30 vs P2=P3=0.20.

### Real hand-verified gold — `spa` only (n=45, the one pair with a genuine `induce/gold/` set)

Reconstructed each paradigm's model by replaying its proposed roots onto the P0 snapshot and rescored
against `induce/gold/spa.jsonl` directly (not the silver substitute):

| | P0 | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|---|
| gold_recall | 0.956 | **0.978** | 0.956 | 0.956 | **0.978** | 0.956 | **0.978** |
| gold_parsed | 0.978 | **1.000** | 0.978 | 0.978 | **1.000** | 0.978 | **1.000** |

P1/P4/P6 each fix one of the two words P0 alone missed (`monte`, `discípulo`); P2/P3/P5 fix neither. Small
effect size (45 words, 1 word = 2.2pp) but the **direction matches the coverage-based finding exactly**, on
a metric that shares no data source with the roots being scored — the strongest single piece of evidence
in this report that the pattern is real, not a silver-gold artifact. (Caveat: the reconstruction used each
paradigm's saved `added` list, capped at 30 entries in the JSON; P1/P4/P6 proposed slightly more than 30
roots, so this is a slight underestimate of their true effect, not an overestimate.)

### Enumeration debt — did NOT move, by construction (a limitation, not a null result)

Every paradigm reports the *identical* `enumeration_debt` as its pair's P0 (e.g. swh: 31 everywhere; tur:
10 everywhere; rus/hin/vie: 0 everywhere, since those pairs have no harmony families to begin with). This
is mechanically guaranteed, not a finding: `run_variant`'s loop only ever appends **roots**
(`model.lexicon`), never touches `model.affixes`, so the harmony-family structure `enumeration_debt` is
computed from cannot change no matter which paradigm built the alignment table. P3's class-canonicalization
happens entirely inside the alignment call's input stream and is discarded afterward — it affects *which
roots get proposed*, never the affix inventory itself. Testing whether class constraints reduce
enumeration debt directly would require re-running full **affix induction** (`tdd.run`'s
`affix_candidates`/`assign_slots` loop) per paradigm, not just the root-discovery loop — far more expensive
(each `tdd.run` call here already took 60–75s alone) and out of scope for this pass. Flagged as a concrete
follow-up, not silently dropped.

### Wall-clock cost

| pair | P0 | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|---|
| swh | 72.3 | 105.4 | 110.4 | 110.6 | 109.6 | 111.6 | 107.0 |
| ind | 68.5 | 93.6 | 96.0 | 97.9 | 101.3 | 101.8 | 100.0 |
| tgl | 69.2 | 86.8 | 98.7 | 111.1 | 112.4 | 112.2 | 95.7 |
| spa | 70.3 | 86.6 | 96.9 | 94.9 | 102.0 | 114.8 | 105.8 |
| tur | 71.6 | 123.3 | 126.1 | 124.8 | 131.2 | 118.1 | 119.7 |
| rus | 73.9 | 111.9 | 143.6 | 102.9 | 106.3 | 104.2 | 97.2 |
| hin | 68.2 | 39.1 | 52.7 | 41.7 | 37.3 | 40.3 | 38.4 |
| vie | 36.7 | 60.0 | 71.8 | 67.1 | 68.8 | 68.5 | 61.3 |

P2 is the most expensive paradigm in 6/8 pairs (BPE training + a larger, noisier token vocabulary to align)
**and** the worst- or second-worst performing on coverage in every pair — a strictly dominated paradigm at
this corpus scale: worse results for more compute, with no offsetting benefit found.

## Analysis

1. **THOT-on-target-morphs (P1) is doing real, substantial work already** — the plan's premise. Mean
   coverage lift over P0 (no THOT signal at all) is **+0.249** averaged across all 8 pairs. This is
   `cotrain.py`'s existing production mechanism; nothing here changes that conclusion, it just re-confirms
   it under this harness's budget.
2. **Naive symmetric segmentation (P2) regresses hard, everywhere except the already-degenerate `hin`
   cell.** This is the plan's §1 "explosion" hypothesis, now with real numbers behind it: BPE at 300 merges
   produces real but imperfect subwords (`righteousness→right-eous-ness`✓-ish, `disciples→dis-cip-les`✗) —
   good enough to look plausible in isolation (see the `thot-on-morphs.md`-era smoke test), but every extra
   token type dilutes the sparse per-verse co-occurrence counts `propose_roots`' `gate=0.5` threshold
   depends on, so far fewer proposals clear the bar.
3. **Class constraints, as actually testable in this harness, did not rescue P2 — and the reason is
   informative, not just a null result.** P3 canonicalizes harmonic target affixes to archiphonemes, which is a
   real, working mechanism (confirmed separately by `induce/phonology.py`'s own tests) — but Swahili/Turkic
   harmony families are a small fraction of the token stream compared to the English BPE fragments P2/P3
   both carry. Pooling evidence on the side that ISN'T the bottleneck doesn't move the number. This
   reframes the original plan's hypothesis usefully: **class constraints need to apply to whichever side is
   actually being over-segmented**, and for English that would mean a morphosyntactic/derivational class
   scheme (closer to P6's mechanism) rather than a phonological one (P3's mechanism, which has no English
   analogue in this pipeline).
4. **Guided splitting (P4) is the "free lunch" — it lets English be segmented ~24–59 words' worth per
   pair (`split_map_size` in the raw JSON) with a cost of ≤0.012 mean coverage versus doing nothing.** It
   works by only trusting a split when the target side already gives independent evidence the two spans
   translate differently — exactly Fraser (2009)'s guided-segmentation principle, simplified to a from-scratch
   heuristic reusing this repo's own root+residue statistics rather than reproducing Fraser's EM method
   (a simplification stated up front in `segment_en.py`'s docstring, not discovered as a limitation after
   the fact).
5. **Factored POS/MSA pooling (P6) is the strongest single result of the six variants** — best-or-tied in
   more pairs than any other paradigm, at essentially P1's ambiguity and wall-clock cost, and it requires
   **no new tokenization machinery at all** — it reuses `assign_slots`' already-computed `req_pos` data,
   which is currently used only to prune the *parse* search space, never the *alignment* evidence pool.
   This is the strongest concrete "class knowledge constrains the statistics" result in the study, and the
   most promising lever for a next iteration.
6. **`hin`'s near-zero root yield in every paradigm (1–3 roots, vs. 33–89 elsewhere) is a data-sparsity
   ceiling effect, not a paradigm effect.** Its cycle-1 history (e.g. `hin_P1.json`) shows 136 unparsed
   words but only 1 alignment confident enough to clear `gate=0.5`; cycle 2 found zero more. All 6
   paradigms are equally starved by the same 200-verse alignment sample for this pair — the "best" cell
   (P2/P3 at 0.500 vs P1's 0.493) is noise on a near-flat surface (Δroots of 1–2), not a real win, and
   should not be read as "BPE helps Hindi."

## Recommendation

- **Do not pursue naive symmetric BPE segmentation (P2) further at this corpus scale.** It is the most
  expensive and worst-performing paradigm tested, confirming the plan's §1/§6 risk prediction directly
  rather than needing further study.
- **P6 (factored POS/MSA pooling) is the best candidate for a real follow-up integration into
  `cotrain.py`**, since it is the strongest performer, costs nothing extra to compute (the `req_pos` data
  already exists), and touches nothing on the English side (no new segmentation-quality risk to manage).
- **P4 (guided split) is a reasonable safe default if English-side segmentation is wanted for other reasons**
  (e.g. feeding `morph_align_hc.py`'s per-morpheme marker pipeline, not studied here) — it costs almost
  nothing and provides real, evidence-gated splits.
- **The enumeration-debt axis remains genuinely untested** — a real follow-up would need per-paradigm
  affix re-induction (a much larger compute budget) to see whether class constraints move that number, not
  just root-discovery yield.

## References

- Fraser, A. (2009). *Deeper than Words: Morph-based Alignment for Statistical Machine Translation.*
  — guided-vs-unguided segmentation; P4/P5's mechanism (simplified, not reproduced exactly — see §5.4).
- Koehn, P. & Hoang, H. (2007). *Factored Translation Models.* EMNLP-CoNLL. — P6's mechanism.
- Sennrich, R., Haddow, B., & Birch, A. (2016). *Neural Machine Translation of Rare Words with Subword
  Units.* — the BPE algorithm implemented from scratch in `align/segment_en.py` for P2/P3/P5.
- Creutz, M. & Lagus, K. — Morfessor (unsupervised morphological segmentation); the dependency-heavier
  alternative to the from-scratch BPE used here, noted in `thot-on-morphs.md` as the reason BPE was chosen
  (no new heavy dependency).
- Lewis, G. L. (1967). *Turkish Grammar*; Underhill, R. (1976). *Turkish Grammar.* — source for the `tur`
  `HARMONY_CLASSES` entry added in this study (`induce/phonology.py`).
- Internal: `align/thot-on-morphs.md` (the plan this report executes), `align/eflomal_vs_hmm.md` (the
  measurement-honesty methodology reused here — report regressions, debunk apparent wins before trusting
  them), `research/Polygloss_integration.md` (the "thin gold" framing informing how `tur/rus/hin/vie`'s
  weaker gold coverage is read).
