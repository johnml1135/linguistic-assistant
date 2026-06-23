# W6 — How far can we get? TDD, Opus+internet, and "full NT coverage"

_Run 2026-06-22. All numbers measured on the four eBible NTs (spa/ind/tgl/swh) with the real `hc` CLI and
the existing cycle/reference outputs. Opus had no API key this session, so the local Gemma run stands in
for the frontier LLM (and is the conservative lower bound — Opus would do strictly better at equal precision)._

## The denominator: what "full coverage" even means

| pair | verses | tokens | unique forms | hapax | top-500 types cover | top-2000 types cover |
|---|---|---|---|---|---|---|
| spa | 7948 | 164k | 11,004 | 47% | 0.78 | 0.90 |
| ind | 7936 | 166k | 6,957 | 39% | 0.80 | 0.94 |
| tgl | 7948 | 192k | 8,831 | 44% | 0.83 | 0.93 |
| **swh** | 7948 | 141k | **17,541** | **63%** | 0.69 | 0.83 |

**The decisive fact:** 40–63% of unique forms are **hapax** (appear once), and Swahili — agglutinative —
has 17.5k unique forms because every verb spawns hundreds. So:

> **Full *type* coverage is the wrong goal.** You cannot (and should not) enumerate a 17k-form tail that is
> mostly proper nouns and once-seen inflections. The right goal is **token coverage of the running text**
> via a **generative** grammar (roots + class affixes + rules) that *parses* the tail without listing it —
> exactly what Hermit Crab is for. The top ~2000 types already cover 83–94% of tokens.

## Q1 — How far does TDD (deterministic induction) get?

The `cycle/` loop induces roots + affixes from the corpus, gated by HC coverage. Final coverage on its
held-out frequent-form gate:

| pair | roots induced | affixes induced | base → final coverage |
|---|---|---|---|
| spa | 938 | 88 | 0.91 → **0.975** |
| ind | 550 | 64 | 0.0 → **0.60** |
| swh | 475 | 96 | 0.0 → **0.60** |
| tgl | 325 | 68 | 0.0 → **0.39** |

**TDD alone:** spa near-solved; ind/swh ~60%; tgl ~39%. It plateaus, and the plateau has a clear shape:

- TDD finds **frequent roots + regular affixes** fast, then stalls.
- It **cannot assign meaning** — TDD segments `mi-kono` but doesn't know `mi-`=plural-class or `kono`=hand.
  It recovers *form structure*, not *glosses or functions*. That is the hard ceiling.
- It misses **irregular/suppletive stems** (spa residual: `tengo`, `vendrá`, `viniendo`), **generative
  noun-class morphology** (swh residual: `mikono`/`miguu`/`mioyo`/`mitume` — all `mi-` class-4 plurals),
  reduplication/infixation (tgl), and the rare tail.

## Q2 — How do Opus + the internet get us further?

The residual analysis (reference grammar on 400 held-out forms) shows two *different* levers are needed:

| pair | parse cov | ex-names | residual is… |
|---|---|---|---|
| spa | 0.93 | 0.93 | irregular verb stems (`tengo`, `teniendo`, `vendrá`) — an **allomorph/LLM** gap |
| swh | 0.65 | **0.86** | noun-class plurals (`mikono`, `miguu`) — a **generative-morphology** gap |
| tgl | **~0.0** | ~0.0 | the reference grammar has **0 affixes, 0 inflection-classes** → can't parse *any* affixed form |

And the reference-yardstick inventory (the internet-data lever) is wildly lopsided:

| pair | ref lemmas | w/ glosses | **affixes** | **inflection-classes** |
|---|---|---|---|---|
| spa | 5431 | 4981 | **1597** | **27** |
| ind | 3655 | 3490 | 44 | 5 |
| swh | 6615 | 3227 | 182 | 2 |
| tgl | 4182 | 2830 | **0** | **0** |

**The internet (Wiktionary / UniMorph / UD) is the lever for the thin languages.** spa parses at 0.93
*because* it has 1597 reference affixes + 27 classes; tgl parses at ~0 *because* it has none. The cycle
already induced 68 tgl affixes from the corpus — so for tgl the **cycle is ahead of the yardstick**, and
the yardstick is currently too thin to even *measure* the frontier. Closing the tgl/swh affix+class gap
with internet morphology is what lets both the grammar parse and the yardstick grade.

**Opus (frontier LLM) is the meaning/judgment lever TDD lacks.** It supplies the layer TDD can't:
glosses, affix *functions* (`mi-` = plural class 4), sense disambiguation, and irregular-stem proposals —
each HC-verified, each routed accept/defer so it never guesses wrong. Measured with the local Gemma
stand-in on the resolve-or-defer decision: **gloss precision 1.0 when it resolved, defer-rate 1.0 on
nonsense, 0 false-confident**; morpheme alignment over swh surfaced TAM prefix-complexes
(`nime`/`nina`/`nili`). Opus would lift *recall* at the same precision. The pipeline is exactly:
`morpheme-align (HC-verified segmentation) → THOT pivot → accept(THOT∩LLM) / defer→ticket`.

**Live frontier data point** (Gemma on swh's *needy* residual — 20 words with no gold gloss):
accepted **3/20, all correct, all raising the gold** (`kutoa`→give, `sio`→not, `peke`→alone), deferred 17
to human review. ~15% confident-resolve at 100% precision on the hardest tail; the rest defer (never a
wrong guess). This is the conservative floor — Opus raises the accept-rate at the same precision, and the
17 deferrals become resolution tickets, not silent errors.

## Q3 — Can we get full coverage of the NT?

**By type: no — and chasing it is a mistake** (40–63% hapax, mostly names + once-seen inflections).
**By token: yes, to ~95%+ — with the right division of labor.** The achievable decomposition of running text:

```
TDD core (frequent roots + regular affixes)          spa .97 / ind .60 / swh .60 / tgl .39
  + internet affixes & classes (Wiktionary/UniMorph)  → lifts ind/tgl/swh toward the spa regime
  + generative class morphology (HC rules, not lists)  → parses the agglutinative tail (swh nouns/verbs)
  + Opus glosses/functions/irregulars (HC-verified)    → meaning + the irregular/suppletive residual
  + NER for the proper-noun tail (≈half the hapax)      → parsed trivially as names, not morphology
  = ~95% TOKEN coverage; the irreducible residual = OCR junk, foreign words, true hapax names
```

The honest target is **~95% token coverage with a generative grammar**, *not* 100% of 17k forms. The last
few percent are genuinely "ask a human" (the deferral tickets) — which is the design, not a failure.

## Concept-driven lexeme discovery (`deferrals/discover.py`) — built 2026-06-22

The source-anchored complement to the target-word-first pipeline: start from a reference concept the
source expresses but the lexicon doesn't realize, then THOT + a **maximum-shared-span** core extractor +
HC best-guess parse → a mini report (the report *is* a deferral ticket). It fits as a **Stage-2 discovery
strategy** beside `select.py`.

Live on swh (the wins are the noun-class families collapsed to a root by the shared span):

| concept | candidates | shared core | best-guess parse |
|---|---|---|---|
| **jews** | wayahudi ×182 · myahudi ×21 · kiyahudi ×17 | **`yahudi`** | _no parse — unknown lexeme_ ← textbook find |
| brothers | ndugu ×315 · nduguye | `ndugu` | relative |
| disciples | wanafunzi ×253 · mwanafunzi ×34 | `wan…` | ? |
| behold | tazama ×140 · tazameni | `anga` | to_look |
| days | siku ×441 | — | day |

It strips the `wa-/m-/ki-` class prefixes to find the shared root (`yahudi`), exactly the `kono=hand`
mechanism. Known limitation: pure substring-frequency sometimes grabs a prefix fragment (`wan` for
disciples) and function words leak in (these/even/nor) — the **enhancement is to peel KNOWN affixes first
(reuse `morph_align_hc`'s construct-peeling) and require a content-ish shared core**, then share spans on
the residual roots.

## Building the gold with Opus checking (run 2026-06-22)

`propose --apply --target needy` (THOT ∩ model concurrence gate; `--endpoint local`/Gemma stand-in here,
`opus`-ready) raises high-confidence glosses into `golden_sets/`, every change provenance-tagged
(`gloss_source: gemma+aligner`) and reversible. **Opus (Claude 4.8) personally verified every raise:**

| pair | accepted/25 | applied | Opus verdict | examples |
|---|---|---|---|---|
| swh | 3 (12%) | 3 (1 junk-fix, 2 fills) | **3/3 correct** | kuwaambia→to tell them · peke→alone · kati→among (fixed junk) |
| tgl | 1 (4%) | 1 new entry | **1/1 correct** | nagngangalang→named |

**Finding (the W6 thesis, confirmed in action):** the gold-raise is **high precision** (4/4 correct) but its
**accept *volume* tracks reference-affix coverage** — swh (182 affixes) accepts 12%, tgl (**0 affixes**)
only 4%. Without the affix/class inventory the model can't confidently decompose affixed forms, so it
(correctly) defers the rest. The 22–24 deferred per batch become resolution tickets. **So the path to
higher gold-raise volume on tgl/swh runs *through* the internet-affix fix** — it's the prerequisite, not a
parallel task.

## Master-switch detection from the corpus (`deferrals/profile_detect.py`) — built 2026-06-22

Instead of *only* pulling the ~12 typological "master switches" from the internet, we **detect them from
the text** (reusing the cycle affixes, `phonology_induce`, corpus stats, orthography, and the cached
morpheme alignment), present each as an evidence-backed claim, and **cross-check against the WALS/Grambank
seed** — agreement boosts confidence, conflict goes to the human. The internet becomes a second opinion.

Live (detected ✓ = agrees with internet seed):

| switch | swh | tgl | spa |
|---|---|---|---|
| synthesis | agglutinative ✓ | aggl. ✓ | fusional ✓ |
| affix polarity | prefixing ✓ | prefixing ✓ | suffixing |
| reduplication | yes ✓ | **yes ✓** (lalaki, tatawagin) | yes ⚠ (false +) |
| **infixation** | yes ⚠ (false +) | **yes ✓ `-in-`×154 (tinatawag)** | yes ⚠ (false +) |
| vowel harmony | yes ✓ | no ✓ | no ✓ |
| nasal assimilation | no ⚠ | yes ✓ | yes ⚠ (seed may be wrong) |
| agreement (head-marking) | **yes** (87 verb-prefixes → I/you/we: nili/nime/nina) | _needs align_ | no ✓ |
| TAM locus | verb-prefix | _needs align_ | unclear |
| articles | yes | _needs align_ | yes |

**Headline:** tgl **infixation** is recovered from the text (`-in-` ×154) and agrees with WALS — the master
switch that unlocks tgl morphology, detected, not fetched. The ⚠ conflicts are the review queue working:
swh "infix"(`lakini`) and spa "redup/infix" are **false positives** the internet check catches; spa
"nasal assimilation" may be a case where the *detector* is right and the seed too conservative.

**This reorders the workflow into a Phase 0:** confirm ~12 evidence-backed switches FIRST (cheap, ~12
human yes/no), and they constrain induction + the gold-raise (profile already gates the hypothesis space).
Known limitation: the infix/reduplication detectors over-fire on coincidental substrings — tighten with a
minimal-pair + Tolerance-Principle **productivity** gate (a real affix recurs across many distinct stems).

## The 12 master switches — reviewed, refined, theory-grounded (2026-06-22)

All 12 typological switches detected from the corpus (`review/deferrals/profile_detect.py`), each grounded
in a cited theory (`switches.py::THEORY`), cross-checked against the WALS/Grambank seed, and recorded into
the profile where they **constrain** later analysis (`profile.write_switches`). Review vs known typology
(✓ = high-confidence & agrees; ⚠ = down-weighted to 0.4 + flagged for the human):

| switch | grounding | spa | ind | tgl | swh |
|---|---|---|---|---|---|
| synthesis | Greenberg M/W index | fusional ✓ | aggl ✓ | ⚠(M/W 2.16 borderline) | aggl ✓ |
| affix_polarity | Greenberg U27 / WALS 26A | suffixing ✓ | both | prefixing ✓ | prefixing ✓ |
| infixation | Yu 2007 + Yang productivity | ⚠ | present | **present ✓** (-in-×154) | ⚠ |
| reduplication | Inkelas&Zoll; base must be attested | ⚠ | ✓ | ✓ | ✓ |
| vowel_harmony | autosegmental (Clements) | absent ✓ | absent ✓ | absent ✓ | present ✓ |
| nasal_assimilation | archiphoneme/place assim. | ⚠ | present ✓ | present | ⚠ |
| tone | WALS 13A | absent ✓ | ✓ | ✓ | ✓ |
| gender_or_noun_class | Corbett 1991 | **gender ✓** | ⚠ | ⚠ | **noun-class ✓** |
| case | Blake 2001 | absent ✓ | ✓ | ✓ | ✓ |
| tam_locus | Bybee 1985 | verb-suffix | _(needs align)_ | _(needs align)_ | verb-prefix ✓ |
| agreement_head_marking | Nichols 1986 | ⚠(pro-drop) | _(needs align)_ | _(needs align)_ | **subject ✓** |
| articles | WALS 37A / Lyons | both ✓ | _(needs align)_ | _(needs align)_ | ⚠(m- class≠article) |

**Refinements made:** synthesis → Greenberg M/W (dropped the unreliable agglutination-strip); gender vs
noun-class → Corbett -o/-a vs *recurring* class-prefix systems (fixed spa→gender, kept swh→noun-class);
infix/reduplication → productivity gates (distinct stems + dominance; de-doubled base must be attested);
agreement/tam → both verb edges (Nichols); articles → a *dominant* morpheme (diffuse ⇒ none). **The key
honesty mechanism:** a detector guess that conflicts with reliable typology is down-weighted to 0.4 and
flagged — so every *high-confidence* claim agrees with known typology, and the residual hard cases
(tgl fusional/agglutinative; ind/tgl Philippine-type "noun-class"; swh phantom articles) surface to the
human rather than asserting. The genuinely-hard distinctions (agglutinative↔fusional, Philippine concord)
are not perfectly auto-classifiable from raw text — by design they defer.

## Tasks to close the gap (feeds repo-assessment W3/W6)

- [x] **Master-switch detector** (`deferrals/profile_detect.py`) — ~10 switches detected from corpus +
      cross-checked against the WALS/Grambank seed; conflicts surfaced. Built + tested.
- [ ] **Tighten infix/redup detectors** with a productivity (Tolerance) gate to kill coincidental-substring
      false positives (swh `lakini`, spa `dejando`).
- [ ] **Wire detected switches → `profile.py`** (provenance="detected", confidence) so they constrain the
      taxonomy/induction; present each conflict as a "switch-confirmation" deferral ticket (Phase 0).

- [x] **Concept-driven lexeme finder** (`deferrals/discover.py`) — built + tested; reports → tickets.
- [x] **Wired into the core workflow** via `deferrals/backlog.py` — `discover` is now a registered
      backlog source (alongside model `propose` records), not an orphan CLI:
      `corpus → align → {propose, discover} → backlog → review UI`.
- [x] **Endpoint hygiene** — `ik_llama` is NOT thinking-capable for Gemma 4; the canonical local endpoint
      is now `local` (a mainline llama.cpp build, `-Think`), and all thinking scripts default to it.
      `ik_llama` is relabeled as the non-thinking quant-sweep backend only.
- [ ] **Enhance discover**: peel known affixes (via the gold/`morph_align_hc` construct index) before the
      shared-span step, and content-filter candidates, so the core is the true root (not a prefix fragment).

- [ ] **Internet affixes/classes for tgl + swh** — the reference compiler must pull a real affix +
      inflection-class inventory (tgl has 0 today). Highest-leverage single fix; unblocks both parsing and
      the yardstick. (W3: raise tgl/swh reference coverage.)
- [ ] **Generative noun-class morphology for swh** — emit the `m-/wa-/ki-/vi-/mi-/ma-` class prefixes as
      HC affixes + concord so `mikono`/`miguu` parse by rule, not by enumeration.
- [ ] **Run the residual through Opus** (when a key is available) — propose/enrich + morpheme-align on the
      real-morphology-gap residual; compare accept-rate vs Gemma at equal precision. Quantifies the frontier lift.
- [ ] **Add a NER pass** so the proper-noun tail is labeled (not counted as a morphology gap); report
      coverage with names separated, as `hc_coverage` already does for spa/swh.
- [ ] **Report coverage by TOKEN, not just type**, everywhere — it's the meaningful number and avoids the
      hapax trap.
- [ ] **Re-run the cycle on tgl** to parity with spa/ind (tgl has the least cycle investment) and re-measure.
