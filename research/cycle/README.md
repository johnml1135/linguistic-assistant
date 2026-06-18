# cycle/ — TDD for grammar

A coverage-gated loop that builds a Hermit Crab grammar from the eBible-derived wordforms, the way the
`steady-state-virtuous-cycle` describes: **Red → Green → Refactor**, with the `hc` CLI as the gate.

```
Red      held-out frequent target wordforms that don't parse (0 analyses)
Green    induce the affix / stem that makes failing forms parse — kept ONLY if HC coverage rises
Refactor keep the grammar minimal; HC search-explosion (chunk timeouts) on bloated affix sets
         shows up as a coverage drop → the gate reverts it (an emergent Occam pressure)
```

Reuses the sibling golden harness (not modified): `golden.grammar.LangModel` + `golden.hc.run_parse`
(the deterministic verifier). The propose step here is a **deterministic inducer** so the loop runs
with no model; it is the seam where the LLM `propose-from-evidence` / `generalize-not-enumerate` skills
plug in later.

## Run
```bash
cd research && PYTHONUTF8=1 python cycle/tdd.py --pair tur --seconds 540
PYTHONUTF8=1 python cycle/tdd.py --pair hun --seconds 540
python cycle/tests_smoke.py   # offline: phonology induction (no hc.exe / network / audio)
```
Outputs: `cycle/out/<pair>_trend.jsonl` (per-iteration coverage/ambiguity) and `<pair>_result.json`
(final coverage, kept affixes, **`harmony_families`** + **`enumeration_debt`** — see below).

Word glosses come from `golden/_sources/ebible/<pair>/glosses.tsv`. With **eflomal** alignment (vs the
co-occurrence fallback) Turkish climbed 0.475 → **0.675** in the same 10-min budget; Hungarian held
**0.95**. Sharper seed glosses ⇒ cleaner roots ⇒ more of the affix budget spent on real morphology.

## The three levers
1. **Affix induction** — frequent residues after the longest known-root prefix become candidate
   suffixes; add a batch, re-parse, keep on coverage gain. Reverted candidates are remembered (no churn).
2. **Root growth** — strip a known suffix off a frequent form → propose the stem as a new root: a form
   can't parse if its stem isn't a root, however many suffixes exist.
3. **Moving-window curriculum** — when a window converges, promote its tested forms to roots and slide
   to the next frequency tranche. This walks the vocabulary and keeps every second of the budget doing
   real HC work (the v1 loop converged at it≈34 then busy-spun to it≈700 — fixed).

## What we learned (and folded back)
- **Coverage-as-test-suite is a genuine TDD gate.** The loop recovers real Turkish suffixes
  (`-i, -ler/-lar, -de/-den/-dan, -ın, -miz, -lık, -nın, -suz, -dır…`).
- **Affix induction *alone* plateaus (~0.27); affix + root-growth + window blows past it** — Turkish
  reached **~0.58 in 40 s and kept climbing**, ambiguity steady at ~2.0. The lesson: you can't add
  morphology one dimension at a time — stems and affixes have to grow *together*.
- **The gate rejects spurious affixes for free** — content words mis-proposed as suffixes (`bir`,
  `çok`) don't raise coverage and are reverted. No hand-curation needed.
- **HC timeouts are a cheap Occam signal.** Too many affixes → unordered-rule search explodes →
  chunk timeouts → coverage falls → revert. The grammar is pressured to stay small *by the engine*.
- **Vowel-harmony allomorph pairs surface as separate suffixes** (`-de/-da`, `-ler/-lar`, `-in/-ın`,
  `-lık/-lik/-luk/-lük`). That is exactly the `generalize-not-enumerate` cue: one phonological rule
  collapses each set — HC v1 here has no phonology, so they're listed and the generalization is the
  clear hand-off point to the LLM proposer.
- **The enumeration debt is now measured, not just asserted.** `harmony_families()` groups kept affixes
  by consonant skeleton (harmony vowels stripped) and `enumeration_debt` counts the redundant
  allomorphs. At the 10-min ceiling **~half the affix budget is harmony variants** — Turkish 63/124,
  Hungarian 60/120. High-confidence multi-consonant families (`lr=lar/ler…`, `nk=nak/nek`) are precise;
  single-consonant ones (`n`, `t`) over-merge distinct morphemes, so it's a *candidate worklist* for the
  generalize step to refine — not an auto-collapse. This is the concrete hand-off payload to the LLM.

## Limits / next
- Roots seeded from surface forms (many inflected) cap coverage; root growth helps but a real run wants
  the LLM proposer + vowel-harmony phonological rules (the `generalize-not-enumerate` skill) to go past
  the deterministic baseline.
- HC is unordered here (`templated=False`) so suffixes stack freely (needed for agglutination) at the
  cost of ambiguity — the assess signal to watch.

## Phonology induction (`phonology.py`)
Phase 1 of the `phonology-induction-loop` OpenSpec change turns the measured `enumeration_debt` into the
optimization target. `harmony_families()` surfaces vowel-harmony allomorph sets; `phonology.py` proposes
one **archiphoneme** affix + a conditioning **natural class** per family (`lar`/`ler` → `lAr` over the
low-vowel class; `nın`/`nin`/`nun`/`nün` → `nIn` over the high 4-way), then *generates* the surfaces and
keeps the collapse only when it regenerates every observed allomorph (coverage holds) and the affix
count drops (Occam). The run result now carries a `phonology` block (`enumeration_debt_before/after`,
`collapsed`, `needs_review`). Text-only and offline — the harmony-rule expander is the oracle; optional
audio (`research/audio/`) can later *confirm* a family's conditioning feature but is never required.
Emitting the classes as HC `NaturalClass` XML and re-verifying through `hc.exe` is the remaining
native-dependent step (see the change's task 1.1).

The loop's audio-side tail (phone feature grounding, human-gated pronunciation promotion, and the
generated-surface vs observed-phones second gate) lives in `research/audio/` (`features.py`,
`promotion.py`); the phone↔grapheme vowel-feature distance metric used by the second gate is
`audio/promotion.py:feature_mismatch_count`. The `hc.exe` generate path that produces the surface to
compare is the remaining native wiring.
