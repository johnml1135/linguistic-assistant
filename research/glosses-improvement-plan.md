# Glosses Improvement Plan (GIP)

Entry point for closing the grammatical-feature blind spot found by the 18-language PolyGloss pilot
(`Polygloss_integration.md`, `corpus/polygloss/out/PILOT_REPORT.md`): across all 18 typologically
diverse languages, the induced grammars produced almost no real grammatical feature labels — only
`PL`/`PST`/`PROG`/`CMPR`, English's own tiny inflectional inventory — despite the gold data documenting
rich case systems (Tsez, Lezgian, Basque), noun-class agreement (Ruuli), evidentiality (Tsez), converbs
(Tsez/Dolgan/Selkup), switch-reference (Mauwake), and dozens of other categories the pipeline never
even attempted to label. Five research passes (§3) investigated the actual state of the art for closing
this gap, one per sub-area. **This document and all five sub-papers are research only — no code was
written or modified producing them.**

---

## 1. What the pilot actually found (grounding)

Mined directly from `induce/out/pg_*_model.json` and `corpus/polygloss/out/*_pilot.json` (not
speculation — every number below is measured from the 18-language pilot run):

- **Affix labels found, total, across all 18 languages: `PL`, `PST`, `PROG`, `CMPR`.** Nothing else.
  The mechanism responsible, `induce/glossing.py::en_morph_diff`, is a hardcoded 6-pattern check
  against English suffixes and cannot structurally produce anything else, regardless of corpus size.
- **Morphotactics (slot order, POS-attachment) worked well**: every language chose an ordered
  "templated" grammar; 50–85% of affixes got a correct attaching-POS. This is NOT the blind spot —
  the system reliably discovers *structure*, just not *meaning*.
- **Phonological natural-class collapse never fired for any of the 18 languages**
  (`harmony_collapsed=0` everywhere, despite real `enumeration_debt` 0–46 per language) —
  `induce/phonology.py::HARMONY_CLASSES` has exactly one hand-authored entry (Swahili).
- **Typological cross-checking (`review/explore.py`'s switch-view) has never run against any of the
  18 pilot languages** — it only has hand-transcribed seed data for 4 of the original 8 production
  languages (`review/deferrals/profile.py::_seed`).
- **Alignment itself failed outright for one language** (Nyangbo: `glossed_frac=0.002`, i.e. THOT
  produced a usable English gloss for 1 of 435 induced roots), with nothing in the pipeline detecting
  this automatically.
- **The reported coverage/parse-rate metrics conflate "parsed" with "parsed AND meaningfully
  labeled"** — this whole analysis had to be done by hand, cross-referencing raw model JSON, because
  no existing metric surfaces the label-poverty finding on its own.

---

## 2. The cross-cutting finding: the tools mostly already exist

The single most important result of the five research passes isn't a new algorithm to build — it's
that **two independently-researched sub-papers, working from different literature bases, converged on
the same top recommendation**: `review/affix_function.py` — which projects English UD morphological
features (Case, Gender, Person, Number, Mood, Voice, and more) onto vernacular affixes via alignment,
graded by held-out prediction accuracy — **already does structurally what the state-of-the-art
classical projection literature (Yarowsky & Ngai, Hwa et al., Täckström et al.) recommends, and has
simply never been run against any of the 18 pilot languages.** `gip-feature-projection.md` reached
this from the IGT/glossing-SOTA literature; `gip-evaluation-calibration.md` reached it independently
from the metrics/calibration literature, and additionally established that a held-out gate on
`en_morph_diff` *alone* — without also replacing its label vocabulary — cannot fix the core problem,
because `en_morph_diff`'s six-tag ceiling is structural, not a confidence issue.

The same pattern repeats elsewhere:

- `review/deferrals/profile.py`'s typological switch-detection machinery (WALS/Grambank cross-checking,
  agree/conflict flagging) already exists and already does the "flag an expected-but-missing feature"
  job `gip-typological-priors.md` was asked to research a fix for — it's hardcoded to 4 languages
  (`spa`/`ind`/`tgl`/`swh`) and falls through silently to an empty, permissive profile for everything
  else, including all 18 pilots.
- `induce/tdd.py::harmony_families()` already generically groups suspected phonological allomorphs —
  the missing piece isn't the grouping, it's the archiphoneme-collapse step, which is gated on a
  one-language hand-authored dict.
- The pilot's own ad hoc `glossed_frac` diagnostic (used manually, after the fact, to catch Nyangbo)
  is already exactly the gold-free alignment-confidence signal `gip-alignment-robustness.md`
  independently arrived at as the standard literature approach — it just isn't automatically computed
  or gated on inside the pipeline.

**Practical implication for prioritization**: the highest-leverage next steps across all five areas are
disproportionately *"run/extend/wire up existing code against the 18 new languages,"* not *"build new
machinery."* §4 orders the unified plan accordingly.

---

## 3. Sub-papers

Each covers one research area in full depth — state of the art, applicability against this repo's
constraints (no torch/GPU in the core loop, symbolic/deterministic-HC-verified induction, 500–37,000
sentence-pair corpora), ranked recommendations, and open questions/risks.

| Sub-paper | Covers | Top finding |
|---|---|---|
| [`gip-feature-projection.md`](gip-feature-projection.md) | Automated interlinear glossing SOTA (SIGMORPHON 2023, GlossLM), classical cross-lingual projection, API-LLM prompting, periphrastic feature recovery | Almost all published glossing SOTA is trained on target-language gold IGT — a differently-shaped problem than this repo's gold-blind induction. The two adoptable threads are classical type-constraint projection (`affix_function.py` already is one) and API-LLM-RAG prompting (fits the existing swappable-endpoint architecture; a 2026 case study found a pure-API-LLM approach beating a locally-trained BiLSTM by 18 points at comparable scale). |
| [`gip-phonology-induction.md`](gip-phonology-induction.md) | Natural-class discovery, morphophonological rule learning, harmony-dimension detection, phonetic feature tooling | Epitran (orthography→IPA) covers only 1 of the 18 pilot languages, blocking most IPA-dependent literature outright. Baker's older HMM/distributional method discovers harmonic vowel classes purely from **orthographic co-occurrence statistics** — the one precedent matching this repo's no-IPA, no-torch constraints exactly. |
| [`gip-alignment-robustness.md`](gip-alignment-robustness.md) | Gold-free alignment quality estimation, eflomal failure modes, cold-start bootstrapping, small-corpus alignment alternatives | No canonical gold-free alignment-quality metric exists, but this repo already independently invented an instance of the standard proxy family (`glossed_frac`). Eflomal ships an unused small-corpus rescue mechanism (`--priors`) whose availability through this repo's `sil-machine` wrapper is unverified. Critically: Nyangbo's failure may be corpus type-sparsity from agglutinative morphology, not an alignment-algorithm problem at all — no aligner-side fix would help if so. |
| [`gip-typological-priors.md`](gip-typological-priors.md) | WALS/Grambank/AUTOTYP/URIEL as priors for grammar induction | `review/deferrals/profile.py` already does WALS/Grambank cross-checking for 4 languages; extending it is a generalization, not a new subsystem. Found a live glottocode-granularity trap (Grambank codes the cluster node `nuuu1241` but not our exact leaf code `nngg1234`) and a real coverage gap (Ruuli — the Bantu noun-class language this task specifically asks about — has zero WALS/Grambank entries). No prior art uses a typological KB to drive a *symbolic* rule-search inducer; that's genuinely unexplored, unlike the "flag the gap" use case. |
| [`gip-evaluation-calibration.md`](gip-evaluation-calibration.md) | SIGMORPHON eval methodology, calibration/held-out gating, data-scaling literature | SIGMORPHON 2023 already has the exact precedent for splitting "structure found" from "label correct" (its Stems/Grams columns) — but the newer paper describing PolyGloss's own corpus doesn't carry that split forward, so adopting it here is ahead of, not behind, the field's own current practice. The real fix for the label-poverty gap is `infer_affix_glosses`'s label *vocabulary*, not just adding a held-out gate to it. The data-scaling question has thin literature support for symbolic induction — recommend mining the pilot's own data instead of importing an external law that doesn't exist in citable form. |

---

## 4. Unified recommended build order

Combines all five papers' rankings into one sequence, ordered by (a) dependency (measurement before
mechanism; cheap validation before larger investment), (b) how many of the five papers independently
flagged it, (c) cost of being wrong. Every item names the file it lands in.

**Tier 0 — free, zero-risk, do first (pure measurement/bugfix, no new machinery):**

1. **Split structural from functional coverage in the reported metrics.** Add a `real_gloss_rate`
   (fraction of parsed words with a non-`?` grammatical-shaped gloss) to `corpus/polygloss/score.py`
   and a model-level "fraction of affixes with a real tag vs. surface-form-only" number to
   `induce/tdd.py::coverage()`. This is the exact number this whole plan had to reconstruct by hand
   from raw JSON — making it first-class means every future run self-reports the gap instead of
   requiring manual archaeology. *(gip-evaluation-calibration.md #1)*
2. **Fix the silent-absent bug in `review/deferrals/profile_detect.py::detect_case`.** Its exception
   handler currently returns the same `"absent"` value for "genuinely checked, found nothing" and
   "the detector errored" — split these so a typological cross-check (or a human) can tell them apart.
   Zero external dependency. *(gip-typological-priors.md #1)*
3. **Mine the pilot's own data for a corpus-size-vs-outcome correlation.** `corpus/polygloss/out/*_pilot.json`
   already has everything needed to check whether Nyangbo's alignment failure and the fixed-budget
   languages' coverage ceilings are smooth functions of corpus size (suggesting a real data/budget
   floor) or true outliers (suggesting a language-specific cause). No new pilot run required.
   *(gip-alignment-robustness.md §4, gip-evaluation-calibration.md #5)*

**Tier 1 — cheap, highest expected payoff (run existing code against the 18 pilots, unmodified):**

4. **Run `review/affix_function.py` against all 18 PolyGloss pilot languages, as-is.** Never done
   before. `FEATURE_KEYS` already includes Case/Gender/Person/Number/Voice — exactly the categories
   the pilot golden vocabularies need. A positive signal on even 3–4 languages (e.g. a real `Case=Erg`
   label on a Tsez/Lezgian suffix with held-out accuracy > 0.5) justifies wiring it into the main
   induction path. This is the single highest-leverage step in the entire plan — independently
   identified by two of the five research passes. *(gip-feature-projection.md §3.1, gip-evaluation-calibration.md #2)*
5. **Promote `glossed_frac` (or an equivalent alignment-confidence diagnostic) to a first-class,
   automatically-computed field on `align/aligner.py::align()`'s return value**, and gate
   `induce/tdd.py::load_glosses`/`induce/cotrain.py` on it so a Nyangbo-style failure warns instead of
   silently producing an unlabeled grammar. *(gip-alignment-robustness.md #1)*

**Tier 2 — medium effort, gated on Tier 1's results:**

6. **Wire `affix_function.py`'s output back into `LangModel.affixes[i].gloss`**, replacing or
   augmenting `en_morph_diff`'s vote — demote `en_morph_diff` to a fallback for the narrow case it's
   actually good at (same-root English lexical inflection), not the primary mechanism. This is the
   actual fix, not just the validation step (4). *(gip-feature-projection.md §3.3, gip-evaluation-calibration.md #2)*
7. **Extend `review/deferrals/profile.py::_seed` from 4 hardcoded languages to a Glottocode-keyed
   Grambank/WALS lookup**, with a Glottolog genealogy-walk fallback for languages like Ruuli with zero
   direct KB coverage. Once this exists, `review/explore.py::switch_hypotheses` starts working for
   `pg_*` pairs with no changes to `explore.py` itself. *(gip-typological-priors.md #2-3)*
8. **Investigate eflomal's `--priors` small-corpus rescue mechanism** — verify whether `sil-machine`'s
   Python wrapper around THOT's native `EFLOMAL` type exposes it at all before attempting to use it on
   Nyangbo or similarly thin languages. *(gip-alignment-robustness.md #4)*
9. **Build orthography-native distributional harmony-class discovery** (Baker-style: a stem-vowel ×
   affix-vowel contingency table over every HC-parsed word, clustered without any IPA conversion) as a
   producer function feeding `induce/phonology.py::HARMONY_CLASSES`'s existing shape. Validate first
   against Swahili's known `E`/`O` classes as a ground-truth check before trusting it on a new language.
   *(gip-phonology-induction.md §3.1)*

**Tier 3 — exploratory, higher uncertainty, smaller/narrower first experiments:**

10. **Extend UD-feature projection to periphrastic pivot constructions** (English modals → `Mood`,
    "was/were + V-ing" → `Aspect=Prog`) in `review/project.py`. No published system does this — a
    genuinely open, unclaimed niche, not prior-art adoption. Measure success the same way
    `affix_function.py` measures everything: held-out accuracy, not rule count.
    *(gip-feature-projection.md §3.2)*
11. **LLM-RAG proposal fallback** for affixes that clear neither `affix_function.py`'s gate nor
    `en_morph_diff`'s — retrieve aligned sentence/word context (not a dictionary lookup — a 2026 case
    study found dictionary-provision *hurt* 3 of 4 models tested), prompt via the existing swappable
    LLM endpoint, and require the candidate to clear the deterministic HC-verification gate before
    acceptance. Never trust the LLM output directly into a golden set. *(gip-feature-projection.md §3.4)*
12. **LLM-proposed, symbolically-verified natural classes** for phonology, using the same
    propose/verify discipline: `induce/phonology.py::expand_archiphoneme()`'s existing regenerate-and-check
    is the correct oracle, unmodified. *(gip-phonology-induction.md §3.3)*

**Explicitly deferred, not recommended to start now:**

- **Typological-prior-guided search-space biasing** (using WALS/Grambank to actively steer
  `induce/tdd.py`'s affix-candidate search, rather than just flagging gaps after the fact) — no prior
  art anywhere uses a typological KB to drive a *symbolic* rule-search inducer this way; it's genuine
  unexplored design work. Wait until Tier 2's flag-the-gap path (#7) shows real value first.
  *(gip-typological-priors.md #5)*
- **Neural aligners (awesome-align, SimAlign) and neural glossers (GlossLM, Tü-CL)** — hard constraint
  violations (torch/GPU, or trained-on-target-gold architecture mismatch). Noted for completeness in
  the sub-papers, not recommended.
- **Subword sampling for alignment** — promising published numbers (matches 100K-sentence word-level
  alignment with 5K sentences + subword sampling) but real added complexity and conceptual tension with
  this repo's morpheme-level induction goals; worth a single narrow experiment on Nyangbo alone if
  Tier 0/1 don't resolve it, not a general pipeline change. *(gip-alignment-robustness.md #5)*
- **MDL-based calibration for affix-gloss acceptance** — structurally the best-fitting calibration
  method for this deterministic pipeline (no stochastic inference needed), but defining a description-length
  cost function for `LangModel` objects is a real, unscoped design task. Check first whether
  `review/deferrals/`'s existing ΔMDL assessment (used for homograph/allomorph resolution) generalizes,
  before building a second, unrelated acceptance criterion. *(gip-evaluation-calibration.md #4)*

---

## 5. Prerequisite bugs found incidentally (not part of the original ask, but real)

The research surfaced two defects worth fixing independent of any new investment:

- **`induce/tdd.py::harmony_families()`'s `_HARMONY_VOWELS` is hardcoded to Latin-script vowels**
  (`set("aeiouáéíóú")`) — by direct code reading (not run/confirmed against live output), this would
  silently fail the same way on the *existing* 8 production languages' non-Latin members (Russian
  Cyrillic, Hindi Devanagari) as it does on the new pilot's Cyrillic languages (Dolgan/Kamas/Selkup).
  Upstream of, and blocking, any script-agnostic phonology-induction work. *(gip-phonology-induction.md §4)*
- **`review/deferrals/profile_detect.py::detect_case`'s exception handler conflates "confirmed absent"
  with "detector errored"** — see Tier 0 item 2 above.

---

## 6. How to read confidence in these documents

All five sub-papers were written with explicit hedging where a claim could not be independently
verified (PDF text-layer extraction failures, unconfirmed author lists, secondary-source-only
citations) — this is intentional and should be preserved when these documents are used to justify
engineering decisions. In particular:

- Per-language training-size figures for the shared-task literature disagree across sources (this
  pilot's own snapshot vs. SIGMORPHON's vs. GlossLM's) — re-derive counts from the actual HF dataset
  snapshot in use (`corpus/polygloss/fetch.py`) before citing an external number.
- Several claims about tool internals (whether `sil-machine`'s eflomal wrapper exposes priors; whether
  Grambank/URIEL's Python bindings behave as documented) are flagged "unverified, needs a spike" rather
  than assumed — treat these as blocking prerequisites for the paths that depend on them (Tier 2 items
  7–8 above), not settled facts.
- Mielke (2008)'s finding that no feature theory characterizes more than 71% of real natural classes
  across 628 languages means any phonology auto-proposer's correct target is "propose real classes,
  correctly decline the rest," not 100% collapse — a residual failure rate is expected, not a bug to
  chase to zero.
