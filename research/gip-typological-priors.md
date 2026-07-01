# GIP: Typological Priors for Grammar Induction (research only, no code changes)

Researches whether typological knowledge bases (WALS, Grambank, AUTOTYP, URIEL/lang2vec) can inform
induction over the 18 new PolyGloss pilot languages (`corpus/polygloss/run_batch.py::LANGUAGES`), where
the pipeline currently finds **zero** grammatical feature labels beyond English's own tiny inflectional
set (PL/PST/PROG/CMPR) even for languages independently documented as case-rich (Tsez, Lezgian, Basque)
or noun-class-bearing (Ruuli). The existing typological-switch machinery
(`review/deferrals/profile_detect.py`, `review/deferrals/switches.py`, `review/deferrals/profile.py`,
surfaced via `review/explore.py::switch_hypotheses`) already does WALS/Grambank cross-checking — but
only against **4 hand-transcribed seed profiles** (`review/deferrals/profile.py::_seed`, lines 150–193:
`spa`/`ind`/`tgl`/`swh` only; `tur`/`rus`/`hin`/`vie` and all 18 `pg_*` pairs fall through to the empty,
permissive `LanguageProfile(pair)` at line 194). This doc grounds what a real fix would look like.

---

## 1. State of the art

### 1.1 The typological knowledge bases themselves

**WALS** (World Atlas of Language Structures, Dryer & Haspelmath, eva.mpg.de) — the original, still the
most cited. 192 features ("chapters", e.g. Ch.49 Number of Cases, Ch.30 Number of Genders, Ch.81/83
Order of Subject/Object/Verb) over ~2,662 languages, but famously **sparse and non-uniform**: most
languages have values for only a handful of chapters, chosen by whichever specialist contributed data for
that feature, not a systematic questionnaire. Verified directly (2026-07-01, `wals.info`): the languoid
pages for our 18 pilot languages resolve and carry a Glottocode field (confirmed `dido1241` for Tsez,
`cayu1261` for Cayuga, `lezg1247` for Lezgian, `basq1248` for Basque, `beja1238` for Beja — i.e. WALS's
own language catalog agrees with the corpus's glottocodes), but the JS-rendered per-feature value table
could not be scraped through `WebFetch` — the practical access path is the **downloadable CLDF dataset**
(`github.com/cldf-datasets/wals`, a `languages.csv`/`values.csv`/`codes.csv` CSV triple keyed by
Glottocode + WALS 3-letter code) or `PyWALS` (`github.com/lmaurits/pywals`, `pip install PyWALS`) — no
authenticated API, no rate limits, static data dump. WALS's Ch.49 (Number of Cases) and Ch.30 (Number of
Genders) are the two chapters that would matter most here, since they carry an actual **count**, not just
a boolean — closer to "expect ~18 case labels" than a plain "case: yes."

**Grambank** (Grambank Consortium 2023, *Science Advances* 10.1126/sciadv.adg6175; grambank.clld.org) —
newer (released 2023), an order of magnitude more systematic: **195 features coded for every one of
2,467 language varieties on a fixed questionnaire**, spanning nominal, pronominal, verbal, and clausal
domains — not "whatever a contributor happened to write up." Concretely relevant features verified by ID:
`GB070` ("Are there morphological cases for non-pronominal core arguments (S/A/P)?"), `GB083` (dedicated
past-tense verb marking), `GB095`/`GB096` (TAM- or verb-class-conditioned argument marking), `GB114`
(bound reflexive marker), `GB187` (productive diminutive). **Important granularity limit**: these are
mostly **boolean presence/absence of a structural pattern**, not an enumerated feature-label inventory —
Grambank tells you "yes, this language has core-argument case," not "here are its 18 case labels." It
narrows the search (confirms a process exists, rules out others) but does not itself hand over a gloss
tag set the way `gold/inflection.py::canon()`'s UniMorph-derived vocabulary does.
Each variety carries **`representation`** (features coded, out of 195) and **`nzrepresentation`**
(features coded present) counts, directly queryable per-language at
`grambank.clld.org/languages/<glottocode>.json` — this turned out to be the single most useful concrete
signal for coverage-checking (used throughout §2.1). Programmatic access: `pygrambank`
(`pip install pygrambank`, `github.com/grambank/pygrambank`) is **curation tooling, not a data mirror** —
it operates on the raw contributor TSV sheets and does not ship the released dataset. The actually useful
artifact is the **CLDF release** (`github.com/grambank/grambank`, a `cldf/` directory with
`values.csv`/`languages.csv`/`parameters.csv`, Glottocode-keyed, plain CSV — loadable with `pandas` or
stdlib `csv`, no package needed) or the flat `docs/Grambank_most_updated_sheet.tsv`.

**AUTOTYP** (Bickel, Nichols et al., `github.com/autotyp/autotyp-data`) — modular, ~260 variables over
1,319 languages (~260k raw datapoints, ~1.7M with derived/aggregated values), deliberately **not**
pre-defined categories (the "autotypology" method builds categories empirically per-module rather than
forcing every language into the same fixed questionnaire the way Grambank does). Ships as JSON + CSV +
a CLDF dataset. Its case/agreement/argument-marking modules are the most granular of the four sources —
closer to what a "predict the actual case labels" system would want — but coverage is the smallest of the
four (1,319 languages vs. Grambank's 2,467 and WALS's 2,662), and it was not possible to verify coverage
for our specific 18 pilot languages in this pass (no per-language web interface equivalent to
`grambank.clld.org` was found; would require pulling the CSV/CLDF dump directly).

**URIEL / lang2vec / URIEL+** (Littell et al. 2017, ACL; Khan et al. 2024, arXiv:2409.18472, COLING 2025)
— not a new fact-collection effort, a **normalization layer over WALS + Ethnologue + PHOIBLE + Glottolog
(+ Grambank + SAPhon in URIEL+)** into fixed-length binary feature vectors, plus phylogenetic/geographic
distance vectors, covering up to 7,970 languages nominally. `pip install lang2vec`
(`github.com/antonisa/lang2vec`, `l2v.get_features(lang_codes, feature_set)`, languages addressed by
ISO 639-3, not Glottocode directly — a mapping step would be needed for our `pg_<glottocode>` pairs).
**The critical caveat, confirmed via the URIEL+ paper**: URIEL has **zero typological feature values for
31% of the languages it lists** — merging four sparse sources doesn't fix sparsity, it just relabels it.
lang2vec's own documentation states real WALS/Ethnologue/PHOIBLE coverage is ~28.9%; the rest of any
"complete" vector is filled by **KNN imputation over the phylogenetic/geographic neighborhood** — i.e. for
a language lang2vec doesn't actually know features for, it's guessing from relatives, not reporting fact.
URIEL+ improves this (integrates Grambank, adds SoftImpute-based matrix completion, documents imputation
confidence) but the fundamental shape — real data thin, vectors dense via inference — is unchanged.

### 1.2 Typologically-informed induction/transfer as an ACTIVE constraint (not just description)

- **Naseem, Chen, Barzilay & Johnson (2010), "Using Universal Linguistic Knowledge to Guide Grammar
  Induction," EMNLP** — the closest classical analogue to what this codebase would want. Universal
  attachment/word-order rules (not per-language WALS lookups, but cross-linguistic universals) are
  encoded as a **Bayesian prior over a PCFG dependency-grammar induction model**, directly shrinking the
  search space for unsupervised parsing, not just scoring the result afterward.
- **Naseem, Barzilay & Globerson (2012), "Selective Sharing for Multilingual Dependency Parsing," ACL** —
  "selective sharing": a target language shares specific grammar parameters (e.g. verb-object order) only
  with source languages that match on the relevant WALS word-order feature, rather than pooling
  indiscriminately. This is a genuine precedent for typology-gated (not typology-blind) parameter sharing.
- **Ammar, Mulcaire, Ballesteros, Dyer & Smith (2016), "Many Languages, One Parser," TACL** — tested
  feeding raw WALS feature vectors directly into a multilingual neural parser as conditioning input, and
  found **less benefit than just learning a per-language embedding from data** — a negative result worth
  citing: naively injecting typological features into a statistical model doesn't reliably help once the
  model can infer the relevant structure from data anyway. The gain from typology shows up more reliably
  in **zero/near-zero-data settings** (langrank-style transfer-language selection, §1.3) than in
  data-rich multilingual joint training.
- **Üstün, Bisazza, Bouma & van Noord (2020), "UDapter: Typology-based Language Adapters," TACL** —
  typological feature vectors (from lang2vec) condition small per-language adapter modules in a shared
  multilingual parser, letting a genuinely low-resource/zero-shot language borrow structure predicted by
  its typological profile rather than its (absent) training data.
- All of the above are **statistical/neural** systems where "prior" means a term in a probabilistic
  objective or a conditioning vector for a differentiable model. None of them is a **symbolic, rule-search
  system** like this codebase's `induce/` — the closest fit in spirit is Naseem et al. 2010's use of
  typology to prune/reweight a discrete hypothesis space, which maps conceptually (not mechanically) onto
  how `review/deferrals/profile.py::LanguageProfile.allows_affix_kind()` already prunes affix-kind
  hypotheses from a **hand-transcribed** typological seed.

### 1.3 Typological vectors for source-language / feature-existence prediction

- **Malaviya, Neubig & Littell (2017), "Learning Language Representations for Typology Prediction,"
  EMNLP** and **Bjerva & Augenstein (2018)** treat missing WALS/URIEL cells as a **knowledge-base
  completion problem** — train an NMT-derived or graph-embedding model to predict a language's likely
  feature value from its neighbors, essentially what lang2vec's KNN imputation formalizes. This is
  directly the mechanism behind "URIEL says 31% of languages have zero real data but the vectors look
  complete" (§1.1) — useful to know because it means a lang2vec query for an obscure pilot language may
  silently return an **inferred**, not observed, value.
  The SIGTYP 2020 shared task ("Prediction of Typological Features," Bjerva et al., arXiv:2010.08246) ran
  this as a formal competition; follow-on work (`data2lang2vec`, arXiv:2409.17373, 2024) still treats it
  as an open, actively-worked problem, not a solved one.
- **Lin, Chen, Lee et al. (2019), "Choosing Transfer Languages for Cross-Lingual Learning," ACL** — the
  `langrank` system (`github.com/neulab/langrank`) ranks candidate transfer/source languages for a
  low-resource target using a learned combination of typological distance (via lang2vec), phylogenetic
  distance, and dataset-size features; explicitly built for exactly the situation this pipeline is in
  (a newly-piloted language with almost no gold) but for the **transfer-source-selection** problem, not
  the **feature-existence-prediction** problem this GIP is scoped to. Structurally adjacent: our pipeline
  already has an implicit pivot-language choice (English, hardcoded via `PAIR_DIR`/`profile.pivot()`);
  langrank-style logic could in principle rank whether an *additional* related gold language (e.g. an
  existing golden set) would help via typological similarity, but that's a distinct, unscoped extension.
- **"The Role of Typological Feature Prediction in NLP and Linguistics" (2024, Computational
  Linguistics/MIT Press)** is a recent survey specifically interrogating whether typological-feature
  prediction from language embeddings is scientifically sound or circular — worth reading before betting
  design decisions on a lang2vec-imputed (as opposed to WALS/Grambank-observed) value.

### 1.4 Bottom line across all four sub-areas

All four knowledge bases are **descriptive catalogs of what's already true of a language** (a lookup
table), not generative models of what induction search should try next. Nothing found treats a
typological KB as an input to a **finite-state/rule-search morphological inducer** the way this codebase's
`induce/tdd.py` operates — every "constraint" precedent in §1.2/1.3 is inside a differentiable/statistical
model (PCFG prior weights, neural conditioning vectors, KNN feature imputation). The applicability gap in
§2 below is real, not just an artifact of an incomplete literature search.

---

## 2. Applicability to this codebase

### 2.1 Coverage of the 18 pilot languages (spot-checked 2026-07-01, primary sources)

Checked Grambank's per-language JSON (`grambank.clld.org/languages/<glottocode>.json`, fields
`representation`/`nzrepresentation` out of 195) and WALS's languoid pages for a sample spanning the
languages named in the task plus a few more for spread:

| Glottocode | Language | Grambank | WALS | Note |
|---|---|---|---|---|
| `dido1241` | Tsez | 174/195 coded (170 non-zero) | present, Glottocode confirmed | near-complete |
| `lezg1247` | Lezgian | **195/195** (194 non-zero) | present | full |
| `basq1248` | Basque | **195/195** (188 non-zero) | present | full |
| `arap1274` | Arapaho | **195/195** (188 non-zero) | present | full |
| `kara1499` | Kalamang | **195/195** (99 non-zero) | — | full |
| `ainu1240` | Hokkaido Ainu | present, coded incl. `GB070`="no morphological cases" | present | full; a real negative case value |
| `japh1234` | Japhug | present (Jacques 2004/2017 sourced) | — | present |
| `beja1238` | Beja | present | present | present |
| `cayu1261` | Cayuga | **absent (404)** | present, Glottocode confirmed | **WALS-only** |
| `ruul1235` | Ruuli | **absent** (not in the full language list) | **absent** (no `wals.info` page found) | **zero typological KB coverage** |
| `nngg1234` | N‖ng (the exact glottocode `run_batch.py` uses) | **absent (404)** | not checked | see below |

Two findings matter more than the raw hit rate (9/11 sampled have real coverage):

1. **Ruuli — the specific language the task asks about (Bantu noun-class) — has no WALS or Grambank
   entry at all**, despite a published grammar (Witzlack-Makarevich et al., Language Science Press,
   *A dictionary and grammatical sketch of Ruruuli-Lunyala*, cited by SIL/Ethnologue/Joshua Project).
   A typological-prior system built for this pipeline would have **nothing to look up** for exactly the
   language the induction gap is most visible on. Ruuli's noun-class system would have to be inferred by
   analogy from sibling Bantu languages (Ganda `gand1255`, itself in Grambank) via genealogy, not a direct
   glottocode hit — i.e. it forces the KNN/genealogical-imputation move (§1.3) on day one, not as an edge
   case.
2. **Glottocode-granularity mismatch is a real, not hypothetical, risk.** Grambank has an entry for
   `nuuu1241` ("Ghaap-Kalahari," a Glottolog **family/cluster node**, 174/195 coded) but **not** for
   `nngg1234` ("Nǁng," the specific leaf language `run_batch.py::LANGUAGES` actually pairs against). A
   naive `if glottocode in grambank_index` lookup would report Grambank has "no data" for `pg_nngg1234`
   even though a typologically near-identical, arguably-the-same-language sibling code is fully coded one
   hop away in Glottolog's tree. Any integration needs a **genealogy walk** (parent/child glottocodes via
   Glottolog, not string equality) to be honest about what "no coverage" actually means.

### 2.2 Practical Python integration path

- **Grambank**: skip `pygrambank` (curation tooling, not a data mirror). Pull
  `github.com/grambank/grambank`'s `cldf/values.csv` + `cldf/languages.csv` (or the flat
  `docs/Grambank_most_updated_sheet.tsv`) once, cache locally under something like
  `research/corpus/typology/grambank/`, and join on Glottocode with plain `csv`/`pandas` — no new runtime
  dependency, no network call in the hot path, consistent with the repo's offline-testable ethos (see
  `corpus/polygloss/tests_smoke.py`'s "no network, no `hc` binary" bar).
- **WALS**: same shape — `github.com/cldf-datasets/wals`'s CSV triple, or `PyWALS` if a package is
  preferred over hand-rolled joins.
- **Glottolog genealogy** (needed for §2.1 finding 2): `pyglottolog` (`pip install pyglottolog`) or the
  `glottolog/glottolog-cldf` CSV dump gives parent-chain lookups so a coverage-check can fall back from a
  leaf glottocode to its containing family/dialect-cluster node instead of reporting a hard miss.
- **lang2vec/URIEL(+)**: `pip install lang2vec`, keyed by ISO 639-3 not Glottocode — would need a
  Glottocode→ISO 639-3 resolution step (Glottolog's own tables carry this mapping) before any lookup.
  Given §1.1/§1.3's imputation caveat, a lang2vec value for one of these 18 languages should be treated as
  **possibly-inferred, not observed**, unless cross-checked against a raw WALS/Grambank cell.
- **AUTOTYP**: CSV/CLDF dump from `github.com/autotyp/autotyp-data`; not evaluated for pilot-language
  coverage in this pass (see §4).

None of this requires a live API or network access at induction time — every source above is a static,
periodically-updated flat-file dump, which fits the "cached rows" pattern `corpus/polygloss/fetch.py`
already establishes for the PolyGloss corpus itself.

### 2.3 Guide-the-search vs. flag-the-gap — both are viable, and the second is cheaper

The task frames three options: (a) bias affix-candidate search, (b) flag "expected-but-missing" as a real
gap for review, (c) seed default feature-label candidates pre-evidence. Given §1.4's finding that no
existing system uses a typological KB to drive a **symbolic** search process, and given
`review/explore.py`'s `switch_hypotheses`/`switch_entries` already implement exactly the "detect from
data, cross-check the internet seed, flag disagreement" shape that (b) describes:

- **(b) is a direct, low-risk extension of existing machinery** — `profile_detect.py::detect()` already
  compares a detected switch value against `_internet_seed(pair)` and drops confidence on conflict
  (`profile_detect.py:350-360`); the only missing piece is a *third* case beyond agree/conflict — "the
  internet seed asserts the feature is present, but the detector never got confident enough evidence to
  assert *any* value" (today `detect_case`'s `except` fallback silently defaults to `"absent"` at
  `confidence=0.4`, which is indistinguishable from a genuinely-checked "no case here" — see
  `profile_detect.py:236-246`). That silent-default-to-absent is the actual bug the task's framing is
  pointing at, and it's fixable without any typological data at all (just don't let "detector errored"
  and "detector confidently found nothing" share a value) — but a WALS/Grambank seed makes the distinction
  sharper: "internet says case is present + detector found nothing" is a stronger, more actionable
  disagreement than today's confidence-drop-only response.
- **(a) is a materially bigger lift.** `induce/tdd.py`'s affix-candidate search and `detect_case`'s
  suffix-family recovery (`review/paradigm/case_detect.py`) are both **evidence-driven bottom-up**
  processes with no hook today for "search harder / lower the acceptance threshold in this specific
  region because the prior says it should be there." Building that hook is a real design task, not a data
  plumbing task, and untested against a symbolic HC-style search space anywhere in the literature found
  (§1.4) — this is genuinely novel for this codebase, not "apply known technique X."
- **(c) is the most fragile of the three.** Seeding default feature-LABELS (not just presence/absence)
  from typology runs straight into the Grambank granularity limit (§1.1): Grambank says "case exists,"
  not "here are ABS/ERG/DAT/GEN/…"; WALS's Ch.49 gives a case *count* at best. Any label set would have to
  come from a different resource entirely (a reference grammar's gloss inventory, UniMorph if it happens
  to cover the language, or an LLM-generated guess) — typology alone under-determines this option.

---

## 3. Recommended paths to investigate, ranked

1. **Fix the silent-absent bug in `review/deferrals/profile_detect.py::detect_case` first, no typology
   needed.** Its `except Exception` fallback (`profile_detect.py:244-246`) returns `Switch("case",
   "absent", 0.4, …)` on any detector failure — identical in shape to a genuine low-confidence "checked,
   found nothing." Split these into distinct states (`"absent"` vs `"undetermined"`) so a downstream
   typological cross-check (or a human) can tell "confirmed no case" from "we don't actually know." Zero
   external dependency, immediately reduces false negatives on the PolyGloss languages regardless of
   whether typological seeding ever lands.
2. **Extend `review/deferrals/profile.py::_seed` from 4 hardcoded languages to a Glottocode-keyed lookup**
   against a locally-cached Grambank CSV (§2.2), replacing the `spa`/`ind`/`tgl`/`swh` if-chain
   (`profile.py:150-193`) with a function that (a) resolves `pair` → Glottocode (already available via
   `run_batch.py::LANGUAGES` / the PolyGloss row schema's own `glottocode` field), (b) walks Glottolog
   parent codes if the leaf glottocode misses (§2.1 finding 2), (c) maps the small set of Grambank
   booleans (`GB070` case, `GB083`/`GB095`/`GB096` TAM marking, noun-class-adjacent features) onto
   `LanguageProfile.feature_space`/`affix_processes` fields, at low confidence + `provenance="Grambank"`,
   never `locked=True` from an automated seed (mirrors how the 4 hand-seeds use `locked` sparingly and
   mostly from `WALS`/`linguist` provenance, not blanket-locking). This is the (b)-flavored, lowest-risk
   path and it's a natural generalization of code that already exists — not a new subsystem.
3. **Wire that seed into `review/explore.py::switch_hypotheses` for `pg_*` pairs.** Today
   `switch_hypotheses` (explore.py:142-166) already renders `doesnt_fit` when `sw.agrees is False`; once
   step 2 gives `pg_*` pairs a real `internet` seed instead of `None`, this view starts working for the 18
   pilot languages with no changes to `explore.py` itself — the CLI (`python -m review.explore --pair
   pg_dido1241 --switches`) would then surface "internet: case=present, detected: case=absent (low
   confidence)" automatically. Confirm this by running it once step 2 exists.
4. **Add a genealogy-aware coverage-gap report, not a full lookup service, for languages like Ruuli with
   zero direct KB coverage.** Rather than building general-purpose typological imputation (§1.3's
   KNN/matrix-completion machinery is itself an open research problem per the 2024 CL survey), a narrow
   `nearest_covered_relative(glottocode)` helper (Glottolog parent-walk, or a same-family sibling already
   in Grambank — e.g. Ruuli → Ganda `gand1255`) that reports "no direct entry; nearest coded relative is
   X, which has case=false/noun_class=true" as an explicitly-labeled inference, surfaced alongside (not
   instead of) the "no data" state, keeps the (c)-flavored temptation ("seed default labels") honest about
   its uncertainty rather than silently guessing.
5. **Defer (a) — search-guidance — until 2–4 show real value.** Given no prior art demonstrates typology
   biasing a symbolic/rule-search induction process (§1.4), this is genuine unexplored design work with
   unclear payoff; building the cheap flag/report path first (2–4) will surface, empirically, which
   pilot languages have real typology-vs-evidence gaps worth the investment before committing to changing
   `induce/tdd.py`'s or `review/paradigm/case_detect.py`'s search behavior itself.
6. **AUTOTYP as a follow-on, not a first pass.** Its case/argument-marking modules are the most granular
   of the four sources (closer to labels than Grambank's booleans) but its coverage of the 18 pilot
   languages is unverified (§2.2) and it lacks Grambank's uniform per-language `representation` count to
   quickly gate "is this language even worth querying" the way §2.1's table did for Grambank — worth a
   dedicated coverage-check pass before investing integration effort.

---

## 4. Open questions / risks

- **Genuinely unverified**: AUTOTYP coverage for these 18 languages (no per-language coverage index like
  Grambank's `representation` field was found for it in this pass) and every non-sampled pilot language
  (Vera'a `vera1241`, Natügu `natu1246`, Nyangbo `nyan1302`, Dolgan `dolg1241`, Kamas `kama1378`, Selkup
  `selk1253`, Mauwake `mauw1238`) — the 6/18 (and Ruuli/Cayuga's mixed result) sampled here is suggestive,
  not exhaustive; a real integration attempt should run the full 18-language coverage check before
  committing design decisions to any specific source.
- **Is Grambank's presence/absence granularity actually useful for this pipeline, or a false lead?**
  §1.1/§2.3 argue it narrows the search (rules in/out a process) but doesn't hand over feature LABELS.
  If the real bottleneck is "we found segmentation but can't name what it means" (per the task's own
  framing — PL/PST/PROG/CMPR only), a boolean "case exists" flag helps the (b) gap-flagging path but does
  ~nothing for actually labeling the affixes correctly — that gap is closer to what
  `align/morph_align_hc.py` + `induce/cotrain.py`'s THOT-gloss-projection machinery already targets (via
  more English-aligned evidence, not typology) than to anything a typological KB provides.
- **The glottocode-granularity trap (N‖ng, §2.1) may not be a one-off.** If Glottolog splits/lumps
  languages differently than the PolyGloss corpus's own `glottocode` field assumes for other pilot
  languages too, a naive per-pair lookup could silently under-report coverage across the batch, not just
  for N‖ng — this needs the genealogy-walk fallback (§3.4) to be trustworthy at all, not an optional nicety.
- **Locking risk**: `LanguageProfile.Feature.locked=True` hard-prunes a hypothesis
  (`profile.py::allows_affix_kind`). An automated Grambank-seeded profile must never set `locked=True` —
  Grambank's own documentation coverage (`representation`/`nzrepresentation`) says nothing about whether
  a given "0" (absent) is a confirmed absence or an under-documented gap in the source grammar it was
  coded from; the 4 hand-seeds in `profile.py` were written by a linguist reading real WALS entries and
  chose `locked` selectively — an automated pass should default to `locked=False` universally until a
  human confirms, which is exactly what `review/explore.py::apply_switch` already exists to do.
- **Not verified**: whether URIEL+'s Grambank integration (§1.1) would make it strictly redundant with a
  direct Grambank CSV pull for our purposes, or whether its imputation adds anything beyond noise for
  languages Grambank already codes directly (Tsez, Lezgian, Basque, Arapaho, Kalamang, Ainu, Japhug, Beja
  all have real, non-imputed Grambank data per §2.1 — URIEL+ would only add value on the languages
  Grambank itself doesn't cover, i.e. Ruuli/Cayuga/N‖ng-as-leaf, exactly where its imputation is least
  trustworthy).
