# induce/ — TDD for grammar (formerly `cycle/`; paths below may still say `cycle/`)

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
cd research && PYTHONUTF8=1 python cycle/tdd.py --pair swh --seconds 540
PYTHONUTF8=1 python cycle/tdd.py --pair ind --seconds 540
python cycle/tests_smoke.py   # offline: phonology induction (no hc.exe / network / audio)
```
Outputs: `cycle/out/<pair>_trend.jsonl` (per-iteration coverage/ambiguity) and `<pair>_result.json`
(final coverage, kept affixes, **`harmony_families`** + **`enumeration_debt`**, and — when a gold set
exists — a **`gold`** block; see below).

**Correctness gate (`gold.py`, `gold/<pair>.jsonl`).** Coverage asks "did it parse?"; the gold gate asks
"did it parse to the RIGHT gloss?" against a small **hand-verified** word→gloss set (independent of the
noisy auto-glosses, so it catches gloss errors). Spanish ships one (`gold/spa.jsonl`, 45 frequent NT
words); a run reports `gold_recall` (correct gloss) and `gold_parsed`. This is the AGENTS.md
correctness signal, stronger than coverage.

**Feature-bearing grammar (Spanish).** For `spa` the cycle emits a grammar with **real phonological
features** (`voc/hi/rnd/back`) + natural classes (vowel/cons/front/high) via
`golden.hc.build_grammar_xml(phon_feats=…)` from `hc_phonology.spanish_phon_feats` — instead of one fake
feature per grapheme. It is layered on the digit-identity segments (additive; other langs keep the
identity-only grammar), giving the substrate future Spanish rules (e.g. the `-s/-es` plural epenthesis,
already induced as two allomorphs) will build on.

Word glosses come from `golden/_sources/ebible/<pair>/glosses.tsv`, built with **statistical alignment**
(THOT HMM; vs the co-occurrence fallback) over the NT (latest build: swh 7948 verses, ind 7936,
tgl 7948, spa 7948 English↔target). Sharper seed glosses ⇒ cleaner roots ⇒ more of the affix budget
spent on real morphology.

## The three levers
1. **Affix induction (both sides)** — frequent residues around the longest known root become candidate
   affixes: a root that is a *prefix* of the word leaves a SUFFIX residue (suffixing langs); a root that
   is a *suffix* of the word leaves a PREFIX residue (prefixing/agglutinating langs). Add a batch,
   re-parse, keep on coverage gain. Reverted candidates are remembered (no churn). Inducing **prefixes**
   (not just suffixes) is what unlocks the non-suffixing targets — see the jump below.
2. **Root growth** — strip a known affix (suffix *or* prefix) off a frequent form → propose the stem as
   a new root: a form can't parse if its stem isn't a root, however many affixes exist. For prefixing
   languages the stem is found by stripping a *prefix*.
3. **Moving-window curriculum** — when a window converges, promote its tested forms to roots and slide
   to the next frequency tranche. This walks the vocabulary and keeps every second of the budget doing
   real HC work (the v1 loop converged at it≈34 then busy-spun to it≈700 — fixed).

**Two-sided induction is the big coverage lever.** The cycle was suffix-only; the four current targets
are mostly prefixing/circumfixing/infixing (Swahili noun-class + TAM prefixes, Indonesian `meN-`/`ber-`,
Tagalog `nag-`/`naka-`), so their morphology sat where the loop wasn't looking. Adding prefix induction
moved coverage sharply: **swh 0.26→0.64, ind 0.22→0.90, tgl 0.20→0.73, spa 0.36→0.88** (≈2–4× budget),
with the Spanish gold correctness gate maintained (recall 0.93, parsed 1.00). Ambiguity rises with the
extra affixes (swh ~4.5; ind/tgl/spa ~2) — the assess signal the affix-template/slot ordering addresses.

## What we learned (and folded back)
- **Coverage-as-test-suite is a genuine TDD gate.** The loop recovers real verb-extension and
  concord affixes (for Swahili, the height-harmony extensions causative `-ish-/-esh-`, stative
  `-ik-/-ek-`, applicative `-i-/-e-`, reversive `-u-/-o-`).
- **Affix induction *alone* plateaus; affix + root-growth + window blows past it.** The lesson: you
  can't add morphology one dimension at a time — stems and affixes have to grow *together*.
- **The gate rejects spurious affixes for free** — content words mis-proposed as affixes don't raise
  coverage and are reverted. No hand-curation needed.
- **HC timeouts are a cheap Occam signal.** Too many affixes → unordered-rule search explodes →
  chunk timeouts → coverage falls → revert. The grammar is pressured to stay small *by the engine*.
- **Height-harmony allomorph pairs surface as separate affixes** (Swahili causative `-ish-/-esh-`,
  stative `-ik-/-ek-`, applicative `-i-/-e-`). That is exactly the `generalize-not-enumerate` cue: one
  phonological rule collapses each set — HC v1 here has no phonology, so they're listed and the
  generalization is the clear hand-off point to the LLM proposer.
- **The enumeration debt is now measured, not just asserted.** `harmony_families()` groups kept affixes
  by consonant skeleton (harmony vowels stripped) and `enumeration_debt` counts the redundant
  allomorphs. High-confidence multi-consonant families are precise; single-consonant ones over-merge
  distinct morphemes, so it's a *candidate worklist* for the generalize step to refine — not an
  auto-collapse. This is the concrete hand-off payload to the LLM.

## Ordered morphotactics (the Refactor step) — `assign_slots`
HC parses all four, but the *unordered* grammar over-generates: with both prefixes and suffixes free to
stack, ambiguity exploded (12–15) and the `amb_cap` was only a band-aid. The Refactor fix is **position
classes**: `assign_slots` learns each affix's slot ordinal from its **co-occurrence order** (greedily
segment frequent words with the induced roots + affixes; root-adjacent = slot 1, next out = slot 2…),
then the grammar is re-emitted as an ordered **affix template** (`golden.hc` `templated=True`,
`morphologicalRuleOrder="linear"`). It is **kept only if ambiguity drops without losing coverage** (the
gate). Measured: Indonesian amb 3.18→**1.83** (coverage 0.933 held), Spanish 2.66→**1.91** — the cycle
recovered real slots (Indonesian `meN-` spread across prefix slots 1–4). The result carries a
`morphotactics` block (unordered vs templated, learned `slots`, `applied`). The judgment is the
[order-the-morphotactics](../../linguistics/skills/order-the-morphotactics.md) skill.

## POS/MSA, morpheme glosses, infixation (the linguistic layers)
- **POS / MSA** (`pos.py`, `assign_slots`, `golden.hc pos_aware`): roots get a coarse POS from their
  English gloss (closed-class sets + verb/adj lists, default noun); each affix's MSA `req_pos` = its
  dominant attached-root POS. The cycle picks the best of {unordered, templated, templated+POS} by lowest
  ambiguity with coverage held, so POS-restriction is adopted only when it doesn't cost coverage (POS is
  recorded on the lexicon regardless). Skill: [assign-pos-and-msa](../../linguistics/skills/assign-pos-and-msa.md).
- **Real morpheme glosses** (`glossing.py`): an affix is relabelled (`-s` → PL) from the English
  inflection diff between root and root+affix glosses — got PL/PST/ADVZ/CMPR (sparse, since aligners
  often gloss to the lemma). **Phonology rules** (`phonology.propose_morphophon_rules`): detects
  Indonesian `meN-` nasal assimilation and Spanish `-s/-es` epenthesis as one-morpheme+rule proposals
  (`result["phonology"]["rules_proposed"]`); the alpha-variable harmony rule is already emitted+verified.
- **Infixation** (`affix_candidates`/`grow_roots` detect `root[0] + INFIX + root[1:]`; `golden.hc` emits
  an HC infix rule, placed in an `infix` template slot): Tagalog induced `-um-`/`-in-`; the infix HC
  round-trip is verified (`tests_hc`).

## Limits / next (what HC still needs to be "happy")
1. **Agreement / inflection features.** POS exists, but affixes carry no number/gender/person/case
   *feature structures* and no concord (Swahili noun-class, Spanish gender/number) is enforced.
2. **HC emission of the proposed phonology rules.** `meN-` nasal assimilation and `-s/-es` epenthesis are
   *proposed* but not yet emitted as HC rules (the alpha-variable harmony rule shows the pattern).
   Reduplication (Tagalog/Indonesian) is the remaining templatic gap.
3. **Correctness gates for all four.** Only Spanish has a hand-verified `gold/` set; `final_coverage` is
   moving-window-dependent, so the (window-independent) gold gate is the metric to trust.

Roots seeded from surface forms (many inflected) also cap coverage; root growth + gloss backfill help,
but the LLM proposer (`generalize-not-enumerate` / `propose-from-evidence`) is what goes past the
deterministic baseline.

## Closing the loop: morpheme alignment → LLM propose → scenarios
- **`morph_align.py`** (feedback edge). The base alignment glosses whole *words* (to the lemma), so
  affixes never get a gloss. After a run dumps its grammar (`out/<pair>_model.json`), `morph_align`
  segments each word into morphemes and **re-aligns English ↔ morphemes** → per-morpheme glosses incl.
  affix functions (`de`→of, `en`→in, `nos`→us). `python cycle/morph_align.py --pair spa [--backend hmm]`.
- **`llm_propose.py`** (judgment). Curates each affix's evidence (side, slot, attaching POS, aligned
  English, examples) and asks a model for a structured analysis (label/category/gloss/confidence/
  rationale). Backend is **swappable by config** via `harness/`: `opus` (claude-opus-4-8) now;
  `vllm`/`ollama` (Qwen 3.6 / Gemma 4) or `ik_llama` later; a deterministic heuristic is the offline
  baseline. `python cycle/llm_propose.py --pair spa --endpoint opus|mock`.
- **Scenarios = the foundation.** Every proposal is banked as a self-contained
  `out/<pair>_scenarios.jsonl` entry (evidence → question → answer, `validated: null`). The curation is
  model-independent, so once answers are validated against external data these become the suite for
  testing small local models. Skill: `propose-from-evidence`.

## Phonology induction (`phonology.py`)
Phase 1 of the `phonology-induction-loop` OpenSpec change turns the measured `enumeration_debt` into the
optimization target. `harmony_families()` surfaces harmony allomorph sets; `phonology.py` proposes
one **archiphoneme** affix + a conditioning **natural class** per family (for Swahili height harmony,
the causative `-ish-`/`-esh-` → `-Vsh-` and stative `-ik-`/`-ek-` → `-Vk-` over the front class
`{i,e}` vs back class `{u,o}`), then *generates* the surfaces and keeps the collapse only when it
regenerates every observed allomorph (coverage holds) and the affix count drops (Occam). The run result now carries a `phonology` block (`enumeration_debt_before/after`,
`collapsed`, `needs_review`). Text-only and offline — the harmony-rule expander is the oracle; optional
audio (`research/audio/`) can later *confirm* a family's conditioning feature but is never required.
Emitting the classes as HC `NaturalClass` XML and re-verifying through `hc.exe` is the remaining
native-dependent step (see the change's task 1.1).

`hc_phonology.py` does exactly that: it emits a feature-bearing HC grammar (`voc/hi/rnd/back` + natural
classes + an underspecified **archiphoneme** + HC alpha-variable harmony rules) and verifies the
collapse round-trips through the installed `hc` — one archiphoneme morpheme parses every surface
allomorph, proven both for a 2-way harmony (the Swahili height-harmony shape `-Vsh-`) and, to exercise
the machinery's reach, a 4-way harmony archiphoneme (`tests_hc.py`, hc-gated/skipped when absent).
Wiring this emitter into the moving-window cycle's eBible-grapheme scaffold needs a per-language feature
inventory for the full charset — the remaining follow-on.

The loop's audio-side tail (phone feature grounding, human-gated pronunciation promotion, and the
generated-surface vs observed-phones second gate) lives in `research/audio/` (`features.py`,
`promotion.py`); the phone↔grapheme vowel-feature distance metric used by the second gate is
`audio/promotion.py:feature_mismatch_count`. The `hc.exe` generate path that produces the surface to
compare is the remaining native wiring.
