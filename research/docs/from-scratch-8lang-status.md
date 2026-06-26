# From-scratch, 8 languages, Opus-as-Reviewer — where we are

Run date: 2026-06-25.

**What actually ran this session (honest provenance):**
- **vie / hin / tur / rus** — induced **from scratch this run** (they had only derived POS before).
  THOT↔HC co-training, bounded budget.
- **swh / ind / tgl / spa** — from-scratch models from a **prior session, restored from backup**.
  A true cold-start of all 8 at once was tried, found too slow *and* it degraded the 4 good models,
  so it was killed and the good models carried over. These 4 were **not** re-induced this run.
- **Coverage below is uniformly re-measured THIS run** for all 8 on the same window (top-1000 words by
  frequency, one HC parse pass), so the column is apples-to-apples regardless of when the model was built.

## Status table (coverage = HC parse rate on top-1000, this run)

| lang | cov | amb | roots/aff | provenance | switches (real signal) | classes | concord | stack |
|------|----:|----:|----------:|-----------|------------------------|---------|--------:|-------|
| **swh** | **0.62** | 3.5 | 475/96 | restored | aggl, prefixing, redup, noun-class, harmony ✓ | **m/wa 814, ma 479, u/wa 402** (real Bantu) | **13/14 clean** | **full** |
| ind | 0.89 | 5.5 | 827/84 | restored | aggl, prefixing, redup, nasal-assim ✓; noun-class ✗flag | orthographic | 0 | induct+switch |
| tgl | 0.80 | 7.5 | 540/56 | restored | aggl, prefixing, redup, **infix ✓**, nasal-assim | orthographic | 0 | induct+switch |
| spa | 0.88 | 3.4 | 915/80 | restored | fusional, suffixing, gender, articles ✓; redup/infix ✗ | orthographic | 0 | induct+switch |
| vie | 0.90 | 2.4 | 842/63 | **this run** | isolating, no redup/infix/harmony ✓ | orthographic | 0 | induct (correct nulls) |
| hin | 0.95 | 2.0 | 1313/51 | **this run** | isolating ✗flag | none | 0 | induct only |
| tur | 0.77 | 1.9 | 515/56 | **this run** | **vowel_harmony ✓**; synthesis=isolating ✗flag | orthographic | 0 | induct only |
| rus | 0.93 | 2.7 | 902/56 | **this run** | aggl, suffixing; noun-class ✗flag, infix ✗ | orthographic | 0 | induct only |

(amb = mean parses per parsed word; ind/tgl are over-generating.)

## The headline finding: coverage ≠ understanding

**Swahili has the *lowest* raw coverage (0.62) yet is the only language where the full discovery
stack lights up** — real Bantu classes (m/wa-, ma-, u/wa-) and 13 clean concord classes (u→wa .85,
m→wa .81). The highest-coverage languages — vie 0.90, rus 0.93, hin 0.95 — extract **zero validated
grammatical schema**. The pipeline parses their words but understands none of their grammar.

That gap is the whole story: induction is solved; *understanding* is not, except for Bantu.

## What the process does well

1. **Induction/coverage works everywhere** (0.62–0.95) with no per-language hardcoding — PAIR_DIR now
   derived from `gold.compile` (fixed in `induce/tdd.py`, `induce/morph_align.py`,
   `review/deltas/emit.py`); full test suite green (190 passed: review/ induce/ align/).
2. **Switch detectors with real corpus signatures work and self-flag.** synthesis, affix_polarity,
   reduplication, infixation, vowel_harmony, tone, gender/noun-class. Where shaky the system raises
   `doesnt_fit` (tur synthesis, rus/ind/tgl noun-class) instead of asserting — correct reviewer behavior.
3. **Swahili end-to-end**: induction → real classes → 13 clean concord. The one full success.

## What is weak / wrong (honest)

- **Spurious switch positives**: spa redup+infix=true, rus infix=true (Romance/Slavic CV coincidences
  past the MIN_STEMS guard).
- **Projection-fed switches null for the 4 new langs** (agreement_head_marking, tam_locus, articles) —
  no syntax projection has been run for tur/vie/hin/rus yet.
- **"Noun classes" for the 7 non-Bantu langs are orthographic first-bigram clusters**, not classes —
  correctly unbacked by concord (fit_none 56–70% for spa/tur/rus).
- hin "final_cov 1.0" reported by cotrain is a 400-sample artifact; true top-1000 coverage is 0.95.
- swh restored model is thin (0.62 top-1000) — a re-induction of swh is worth doing.

## THE biggest next gap

**The higher-level discovery layer only understands prefixal noun-class concord (Bantu). It is blind
to every other paradigm system — case, gender/number agreement, voice/focus — which is where the
grammar of the other 7 languages actually lives.**

Case is the cleanest instance:
- `detect_case` (`review/deferrals/profile_detect.py:221`) is a **hard-coded stub** — returns
  `"absent"` for every language. Turkish (6 suffixal, harmony-conditioned cases) and Russian
  (6 cases × 3 genders) both report case=absent, never even flagged.
- There is **no declension/paradigm explorer** analogous to the noun-class+concord explorer. So for
  the suffixing majority (tur/rus/spa) the system parses words but extracts no validated schema.

But it is broader than case: ind/tgl's real morphology is **voice/focus affixation** (the system
already detects tgl infixation — the right thread to pull), spa's is **gender/number agreement**. The
unifying gap is **no non-Bantu paradigm discovery**.

### Concrete fix (suffixal mirror of the Bantu explorer)

1. A real `detect_case`: a recurring final-syllable set that **co-varies with projected subject/object
   role** (reuse the existing projection edges) is the case signature.
2. A **paradigm hypothesis generator**: group suffixes that co-occur on the same stems into paradigm
   cells, conditioned by gender (rus) or vowel harmony (tur), emitting the same A/B/C + fit-none
   surface the noun-class explorer emits, so Opus-as-Reviewer can adjudicate.

**Start with Turkish**: lowest coverage (0.77), cleanest suffix boundaries (agglutinative), and
harmony-conditioned case — the most legible first target, and the one currently understood least.
