# Gloss-Improvement Plan (GIP) — Feature Projection for Affix Glosses

Research on why `induce/glossing.py::en_morph_diff` only ever emits `PL`/`PST`/`PROG`/`SUPL`/`CMPR`/
`ADVZ` (English's own inflectional inventory, hardcoded as 6 suffix-diff rules), what the field's actual
state of the art does instead, and which of that is adoptable inside this repo's constraints (symbolic
core, no torch/GPU, gold-blind induction, 500–37,000 sentence pairs per language). Written after piloting
18 PolyGloss languages (`Polygloss_integration.md`) whose golden feature vocabularies are dominated by
CASE, GENDER/NOUN-CLASS, PERSON/NUMBER agreement, EVIDENTIALITY, SWITCH-REFERENCE, and TAM values English
does not morphologically mark — none of which `en_morph_diff` can ever produce, structurally, regardless
of corpus size.

**Framing that matters for everything below:** almost the entire published SOTA for automated interlinear
glossing (§1.1, §1.2) is *supervised on target-language gold IGT* — it trains directly on
`(transcription, segmentation, glosses)` triples in the language being glossed, or pretrains at massive
multilingual scale on exactly that triple format (PolyGloss, ODIN, IMTVault are literally their training
data). This codebase's induction path is **gold-blind**: `induce/tdd.py` never sees target-language gold,
and by the time an affix needs a function label, HC has *already segmented it correctly* (verified against
a real parser). The open problem here is narrower than "segment and gloss an IGT line" — it is "assign a
grammatical meaning to an affix whose *existence and position* are already known, using only a pivot
translation and word alignment." Most of the shared-task literature answers a harder, differently-shaped
question than the one this repo has. Say this plainly rather than importing SIGMORPHON techniques that
don't transfer.

---

## 1. State of the art

### 1.1 SIGMORPHON-style supervised IGT generation

The **SIGMORPHON 2023 Shared Task on Interlinear Glossing** (full author list not independently
confirmed from search results — cite by title/venue, not by name, until read directly) is the direct ancestor of the PolyGloss/ODIN/IMTVault data this repo pilots against.
Findings paper: [aclanthology.org/2023.sigmorphon-1.20](https://aclanthology.org/2023.sigmorphon-1.20/);
baseline paper: [arxiv.org/abs/2303.14234](https://arxiv.org/abs/2303.14234). Six typologically diverse
languages — Arapaho, Gitksan, Lezgi, Natügu, Tsez, Uspanteko — two tracks (closed = only shared-task data,
open = external resources allowed). *Caveat: the findings-paper PDF's results tables did not extract
cleanly via automated fetch (binary/compressed stream); the per-language sizes below are sourced from a
secondary paper ("Multiple Sources are Better Than One: Incorporating External Knowledge in Low-Resource
Glossing," author list not independently confirmed from search results,
[arxiv.org/abs/2406.11085](https://arxiv.org/abs/2406.11085)) rather than the primary findings table, and
should be treated as approximate — a different secondary source (GlossLM) reports different Arapaho/Gitksan
counts, see below.*

| Language | Train | Dev | Test | (2406.11085) |
|---|---|---|---|---|
| Arapaho | 39,501 | 4,938 | 4,892 | |
| Gitksan | 31 | 42 | 37 | |
| Lezgi | 701 | 88 | 87 | |
| Natügu | 791 | 99 | 99 | |
| Tsez | 3,558 | 445 | 445 | |
| Uspanteko | 9,774 | 232 | 633 | |

(For comparison, `Polygloss_integration.md` §1 recorded Arapaho 36,776 / Gitksan 89 from a *different*
snapshot of the corpus — the numbers genuinely disagree across sources/dataset versions, not a
transcription error on either side.)

The baseline is a transformer sequence-labeling model. The winning system, **Tü-CL** (Girrbach 2023,
[aclanthology.org/2023.sigmorphon-1.17](https://aclanthology.org/2023.sigmorphon-1.17/)), used a hard-
attention model with straight-through gradient estimation, jointly learning an unsupervised shallow
morpheme segmentation and gloss prediction; +23.99 pts over baseline (closed), +17.42 pts (open).
**LISN** ([aclanthology.org/2023.sigmorphon-1.21](https://aclanthology.org/2023.sigmorphon-1.21/), Okabe &
Yvon) is the one classical/lightweight entry worth naming: **Lost**, a linear-chain CRF variant originally
built as a probabilistic translation model, adapted to glossing by dynamically extending the label
inventory with candidate lexical glosses pulled from the translation line — reported as "very competitive,
especially in low-resource settings," i.e. it does not need the gloss vocabulary fixed in advance the way
a plain sequence tagger does. Earlier classical work, **Moeller & Hulden 2018**
([aclanthology.org/W18-4809](https://aclanthology.org/W18-4809/)), found a plain CRF+majority-label hybrid
*outperforms* an LSTM on this exact low-resource-glossing task — a useful, if dated, data point that
classical structured prediction is not obviously worse than neural at this data scale.

All of these — Tü-CL, Lost, Moeller & Hulden's CRF — are trained end-to-end on gold
`(word, segmentation, gloss)` triples in the target language. None of them is a drop-in for "label an
affix HC already segmented" without restructuring the problem as target-language-supervised in the first
place (see the framing note above, and the CRF caveat in §2).

### 1.2 Neural/LLM-based glossing (GlossLM, Wav2Gloss, and 2024–2026 follow-ons)

**GlossLM** (EMNLP 2024, author list not independently confirmed from search results,
[arxiv.org/abs/2403.06399](https://arxiv.org/abs/2403.06399)) is the
direct successor: a **450k-example, 1,800-language** corpus (ODIN 84k/936 langs, SIGMORPHON-ST 69k/7
langs, IMTVault 80k/1,116 langs, APiCS 16k/76 langs, UraTyp 1.7k/35 langs, Guarani 803/1 lang — Arapaho
alone is ~20% of the corpus by volume) used to continually pretrain **ByT5-base** (582M params, byte-level,
multilingual). Input format explicitly includes the **metalanguage translation** alongside transcription
and segmentation status — the paper states translations "have been shown to provide benefits in gloss
prediction," though no clean ablation isolates how much. Reported morpheme/word accuracy on unsegmented
input: Arapaho 82.1/81.5, Tsez 83.6/87.3, Uspanteko 78.6/81.0 (in-domain, i.e. seen in pretraining);
Gitksan 10.1/28.4, Lezgi 57.3/64.9, Natügu 62.8/78.9, Nyangbo 87.4/86.2 (out-of-domain/held-out). Gitksan's
collapse (10.1% morpheme accuracy) despite reasonable word accuracy is itself informative: at ~31–89
training examples, even a 582M-parameter multilingually-pretrained model does not generalize morpheme-level
labels reliably — a hard floor, not a tooling gap.

**Wav2Gloss** (He et al., ACL 2024, [arxiv.org/abs/2403.13169](https://arxiv.org/abs/2403.13169)) targets a
different problem — end-to-end speech→(transcription, segmentation, gloss, translation) — introducing the
37-language **Fieldwork** corpus. Not directly applicable here: this repo starts from text, not audio, and
Wav2Gloss's four-task cascade doesn't change how gloss *labels* are assigned once segmentation exists.

The genuinely load-bearing thread for this repo is the **API-LLM-prompting** line, because it requires no
target-language training data and no local GPU:

- **"Prompt and circumstance"** (2025, author list not confirmed from search results — cite by title/URL,
  [arxiv.org/abs/2502.09778](https://arxiv.org/abs/2502.09778))
  prompts **GPT-4o via API** word-by-word with retrieval-augmented in-context examples (exact-match +
  approximate longest-common-substring match against training data, reverse-indexed translation words,
  empirical tag-frequency priors) — explicitly *not* assuming segmentation is given. Beats the SIGMORPHON
  baseline at morpheme level on all 7 languages; falls short of Tü-CL at word level except Arapaho; 3-best
  oracle beats Tü-CL on 5/7. Authors explicitly rejected open-weight models ("Llama and other open models
  perform poorly on linguistic tasks unless fine-tuned") — the capability is API-frontier-model-dependent.
- **"Can we teach language models to gloss endangered languages?"** (EMNLP 2024 Findings, author list not
  independently confirmed, [arxiv.org/abs/2406.18895](https://arxiv.org/abs/2406.18895)) — sentence-level in-context learning,
  finding current LLMs still struggle on endangered languages relative to high-resource ones, and that
  *targeted example selection* (not just more examples) is what moves the needle.
- **"Multiple Sources are Better Than One"** ([arxiv.org/abs/2406.11085](https://arxiv.org/abs/2406.11085))
  layers translation encoders (BERT/T5), external bilingual dictionaries, and LLM post-correction
  (GPT-4/Llama-3, in-context) on top of a neural base. Two results worth carrying forward even though the
  base model is neural: (a) translation-conditioning alone gives +3.97 pts average, +9.78 pts in a
  simulated 100-sentence ultra-low-resource setting (Gitksan +7 pts); (b) *dictionary integration* (word
  lists, not full IGT) adds a further +6.53 pts on the 3 languages tested — i.e. even a thin external
  lexicon measurably helps at this data scale.
- **"Hybrid Neural-LLM Pipeline for Morphological Glossing"** (Jungar Tuvan case study, 2026,
  [arxiv.org/abs/2603.00923](https://arxiv.org/html/2603.00923v1)) is the cleanest illustration of the
  constraint split. 895 sentences, 85/15 split. BiLSTM-CRF baseline (requires torch/GPU to train): 0.474
  accuracy. Pure retrieval-augmented LLM prompting (commercial API, **no local GPU**): 0.658. Hybrid
  (BiLSTM + LLM post-correction): 0.698. The GPU-requiring half of the pipeline is the *weaker* half — the
  API-only half alone beats it by 18 points. Also: providing an explicit morpheme dictionary to the LLM
  *hurt* 3 of 4 models tested, suggesting retrieved in-context examples carry more signal than lookup
  tables at this scale — a genuinely counter-intuitive, concretely actionable finding.

### 1.3 Classical annotation/feature projection

The foundational line predates all of the above and is architecturally closer to what this repo already
does. **Yarowsky, Ngai & Wicentowski 2001** ("Inducing Multilingual POS Taggers and NP Bracketers via
Robust Projection Across Aligned Corpora," NAACL 2001) is the origin of "project annotations across a
word-aligned parallel corpus" as a technique — IBM Model 3 alignment, English→Chinese/French, projecting
POS tags and NP brackets, explicitly framed as producing *noisy* labels that need robust downstream
handling, not ground truth. **Hwa, Resnik, Weinberg, Cabezas & Kolak 2005** ("Bootstrapping Parsers via
Syntactic Projection across Parallel Texts," *Natural Language Engineering* 11(3),
[DOI 10.1017/S1351324905003840](https://doi.org/10.1017/S1351324905003840)) extends this to syntactic
dependency structure, and is the paper that introduces the "direct projection is too noisy, add
generalization rules to smooth it" pattern — directly analogous to what a feature-labeling gate over noisy
THOT alignment needs. **Täckström, McDonald & Uszkoreit 2012** ("Cross-lingual Word Clusters for Direct
Transfer,"[aclanthology.org/N12-1052](https://aclanthology.org/N12-1052/)) and **Täckström, Das & Petrov
2013** ("Token and Type Constraints for Cross-Lingual POS Tagging," *TACL*,
[transacl.org/ojs/index.php/tacl/article/view/44](https://transacl.org/ojs/index.php/tacl/article/view/44))
are the key noise-handling refinement: distinguish **token constraints** (per-instance projected tags,
noisy) from **type constraints** (aggregate a *distribution* over tags per word type across all its
aligned instances, keep only tags clearing a probability threshold) — type-level aggregation is
specifically what damps single-alignment noise. They also report that **restricting to 1:1 alignments**
(discarding many-to-one/one-to-many links) measurably reduces noise versus using all alignment links,
at the cost of coverage. **Fang & Cohn 2016** ("Learning When to Trust Distant Supervision,"
[arxiv.org/abs/1607.01133](https://arxiv.org/abs/1607.01133)) goes one step further: an explicit debiasing
layer, jointly trained on a small (1,000-token) gold-tagged set plus the noisy projected set, that learns
*which projected labels to trust* rather than applying a single global threshold — evaluated successfully
on real low-resource languages (Malagasy, Kinyarwanda), not just simulated ones.

`review/affix_function.py`'s design — project English UD features over THOT alignment, then require
**held-out prediction accuracy** on unseen verses rather than trusting the training-split statistic — is
architecturally a **held-out-validated type-constraint filter with a lift+support+share gate** (`LIFT_MIN
= 1.6`, `MIN_SUPPORT = 6`, `MIN_SHARE = 0.30`, `review/affix_function.py:28-33`). This is a reasonable,
independently-arrived-at instance of the Täckström-style type-constraint pattern; it does not currently
do 1:1-alignment filtering, and it does not do Fang & Cohn's joint-debiasing-with-a-little-gold approach
(nothing in this repo's induction path assumes any target-language gold exists — Fang & Cohn's method
would only be applicable to the PolyGloss pilot languages, which *do* have gold, not the 8 production
eBible languages).

### 1.4 Periphrastic/discourse-level feature recovery from prose translation

This is the thinnest area, and the honest finding is: **published, general-purpose systems that explicitly
parse periphrastic constructions in a pivot translation (e.g., detect "must go" → obligative mood, "was
walking" → progressive aspect via rule/parse-based reasoning) and project the *result* onto an unsegmented
vernacular sentence do not appear to exist as a distinct research thread.** What the neural glossing
literature (§1.2) does instead is different in kind: it feeds the entire prose translation as **encoder
input** to a black-box sequence model (GlossLM's ByT5, "Multiple Sources"'s BERT/T5 translation encoder)
and lets attention learn whatever correlation is useful, with no explicit intermediate representation of
"this translation expresses progressive aspect." No paper found decomposes that correlation into an
interpretable periphrasis-detection step. This absence is itself the finding, not a search failure — two
adjacent, partially-relevant facts:

- Universal Dependencies' own feature inventory *does* have a `Mood` value slot for necessitative/optative/
  etc. ([universaldependencies.org/u/feat/Mood.html](https://universaldependencies.org/u/feat/Mood.html)),
  but in practice English UD treebanks annotate `Mood` extremely sparsely on modal verbs — spaCy's English
  morphologizer (what `review/project.py::_spacy_parser` calls, `t.morph.to_dict()`) does not reliably
  populate `Mood` for "must"/"should"/"can" the way it populates `Tense`/`VerbForm` for finite/participial
  verbs. Confirmed by inspecting `review/project.py:37-47` and cross-checking against UD's feature
  documentation, not by finding a paper that measures it.
- "Annotating Tense, Mood and Voice for English, French and German" (ACL 2017 System Demonstrations,
  [aclanthology.org/P17-4001](https://aclanthology.org/P17-4001/); author list not independently confirmed
  — its PDF did not extract cleanly via automated fetch here, and no search result gave a reliable author
  list, so no name is attributed pending a direct read) exists as a rule-based TAM-annotation *tool* whose
  exact method for modal/periphrastic detection is unverified beyond the title/abstract-level description
  available in search results — the closest thing found to "explicit rule-based periphrasis→feature
  mapping," but not independently confirmed in detail and not integrated with cross-lingual projection.

The practical implication: this sub-area is not "adopt paper X," it's "there may be a small, unclaimed
research niche" — see §3.2.

---

## 2. Applicability to this codebase

| Approach | No-torch/no-GPU fit | Low-resource fit (500–37k pairs) | Role here |
|---|---|---|---|
| Tü-CL hard-attention (§1.1) | No — needs a trained neural sequence model, and needs target-language gold IGT to train on | N/A — architecture mismatch, not a data-volume mismatch | Neither. The induction path is gold-blind; adopting this means abandoning that design, not tuning a hyperparameter. |
| LISN "Lost" CRF, Moeller–Hulden CRF (§1.1) | Yes, technically (CRFs are cheap, `sklearn-crfsuite`/`pycrfsuite`, no GPU) | Yes — reported as competitive specifically in low-resource settings | **Tempting but architecturally divergent.** A CRF glosser trains on gold `(word, gloss)` pairs in the target language — the PolyGloss *pilot* languages have that gold (§6 of `Polygloss_integration.md`), so it is *possible* to bolt on as a parallel, gold-supervised glossing path for pilot languages specifically, but it would not touch the 8 production eBible languages (no gold there) and would be a second, differently-shaped subsystem next to `induce/`+`affix_function.py`, not an extension of either. Flag as open question (§4), not a recommendation. |
| GlossLM (§1.2) | No — 582M-param ByT5, needs GPU to run inference at any reasonable speed, needs `transformers`+torch | Its whole point is escaping low-resource limits via massive multilingual pretraining, so nominally yes for accuracy, but the mechanism (pretrain-then-finetune) doesn't match "500 sentence pairs, no GPU" | Neither, directly. Its *finding* (translation-as-context measurably helps, dictionary lookups help) is worth carrying into a symbolic redesign even though the model itself isn't adoptable. |
| Wav2Gloss (§1.2) | Irrelevant axis — it's a different input modality (speech) | N/A | Neither — wrong problem (this repo starts from parallel text, not audio). |
| API-LLM prompting: Prompt-and-circumstance, Ginn ICL, dictionary+LLM layer of "Multiple Sources," Jungar-Tuvan RAG-LLM half (§1.2) | **Yes, cleanly** — an API call to a frontier model is not a local-GPU dependency; this repo already has a swappable LLM endpoint (`llm-hosting-swappable-endpoint` memory: offline-review/online-propose, SIL-hosted default + BYOK-frontier via injected `IChatClient`) that this fits inside without new infrastructure | Yes — these papers' whole premise is scarcity (dozens to a few hundred examples); the Jungar-Tuvan comparison (RAG-LLM 0.658 vs BiLSTM-GPU 0.474 at 895 sentences) is direct evidence the API-only half is not just acceptable but *better* at this scale | **Addition, not replacement.** Best framed as a proposer feeding `review/deferrals/` or the existing `llm_propose.py` pattern for affixes `affix_function.py` fails to label (low support/lift) — a confidence-gated fallback, not the primary mechanism, since the deterministic HC-verification gate is load-bearing and an LLM guess must still clear it or get deferred. |
| Yarowsky/Ngai, Hwa et al., type-constraint projection (§1.3) | Yes — pure statistics over an alignment table, exactly what `align/aligner.py` + `affix_function.py` already are | Yes — this *is* the low-resource-appropriate branch of the whole literature; explicitly designed for noisy, thin alignment | **Already the architecture of `affix_function.py`.** The applicable refinements are incremental, not a new mechanism: 1:1-alignment restriction (Täckström), type-vs-token distinction (already partially present via the train/held-out split, but not via aggregating per-*word-type* distributions the way Täckström does), and — only for languages with some seed gold (the pilots) — Fang & Cohn-style joint debiasing. |
| Fang & Cohn distant-supervision debiasing (§1.3) | Yes | Yes (designed for ~1,000 gold tokens + parallel data — close to what a promoted PolyGloss pilot language would have) | Addition, gated on gold existing — applicable to promoted PolyGloss golden sets (`golden_sets/pg_<glottocode>/`, not yet populated per `Polygloss_integration.md` §6.4), not to the 8 gold-blind production languages. |
| Rule-based TAM/periphrasis tool, P17-4001 (§1.4) | Plausibly yes (rule-based, no GPU implied by the description, unverified in detail) | Orthogonal — it's a pivot-side (English) tool, so its cost doesn't scale with target-language data | Speculative addition — see §3.2. Not verified enough to recommend confidently; the more grounded first step is extending existing UD-feature projection, not adopting an unverified external tool. |

---

## 3. Recommended paths to investigate

Ranked by (a) how directly it closes the PL/PST/PROG/CMPR gap, (b) how much is already built.

### 3.1 Run `review/affix_function.py` against the 18 PolyGloss pilot languages (highest priority, cheapest)

This is the single most obvious next step and, notably, has never been done — `affix_function.py` has
only ever run against the 8 production eBible languages (swh/ind/tgl/spa/tur/rus/hin/vie). The 18 pilot
languages (`corpus/polygloss/out/PILOT_REPORT.md`) are exactly the typologically diverse set (ergative
case in Tsez/Lezgian/Basque, noun-class agreement in Ruuli, TAM in Kalamang/Mauwake) where `en_morph_diff`
structurally fails and UD-feature projection might structurally succeed, because `FEATURE_KEYS` already
includes `Case`, `Gender`, `Person`, `Number`, `Voice` — the exact categories the pilot golden feature
vocabularies need and English inflection cannot supply.

- **File:** new driver analogous to `corpus/polygloss/run_batch.py`, calling
  `review.affix_function.induce_affix_functions(pair, pivot="en", ...)` per pilot pair (the pairs already
  exist in `induce.tdd.PAIR_DIR` from `corpus/polygloss/build.py`'s impersonate-a-pair step, §4.3(a) of
  `Polygloss_integration.md`).
- **First experiment:** for each of the 18 languages, compare `n_labelled/n_affixes` and mean
  `heldout_accuracy` from `affix_function.py` against the number of grammatical tags `en_morph_diff`
  currently produces (almost certainly near-zero for most, since PL/PST/PROG/CMPR are unlikely to be the
  gold feature vocabulary for e.g. Tsez ergative case). A positive signal on even 3–4 languages (e.g. a
  clear `Case=Erg` labelling on a Tsez/Lezgian suffix with heldout_accuracy > 0.5) is enough to justify
  wiring this into the induction path as a default step rather than a standalone CLI.
- **Risk to watch:** `_project_rows` depends on `review.project.get_parser("en")` (spaCy `en_core_web_sm`)
  succeeding and on THOT alignment density — languages already flagged in the pilot report as
  alignment-starved (Nyangbo, `glossed_frac=0.002`) will predictably fail here too, for the same reason,
  not a new failure mode.

### 3.2 Extend UD-feature projection to periphrastic pivot constructions

Given §1.4's finding that no existing system does explicit periphrasis→feature parsing before projection,
and that PolyGloss's `translation` field is full prose (not pre-glossed), this is a genuinely open,
tractable piece of engineering rather than an adoption of prior art:

- **File:** `review/project.py` (alongside `label_tam`, which already establishes the pattern of deriving
  one feature — Tense — from the pivot parse) and `review/affix_function.py` (which consumes
  `p.get("feats", {})` from `project_verse`).
- **First experiment:** add a small, explicit rule layer detecting English modal auxiliaries ("must"/
  "should"/"have to" → `Mood=Nec`, "may"/"can" → `Mood=Pot`) and periphrastic aspect ("was/were + V-ing" →
  `Aspect=Prog` already partly inferable from `VerbForm=Ger` on the main verb plus `Tense=Past` on the
  auxiliary, "have + V-en" →
  `Aspect=Perf`) directly on the spaCy token stream in `_spacy_parser`/`project_verse`, since §1.4 confirmed
  spaCy's morphologizer does not populate `Mood` for English modals on its own. This is new code in the
  existing projection layer, not a new subsystem, and immediately widens `FEATURE_KEYS` coverage for
  languages with modal/evidential/mood morphology (a chunk type the pilots are rich in — Nakh-Daghestanian,
  Papuan) that UD's raw morphological features under-annotate for English.
- **Explicitly speculative:** treat as a research spike, not a committed feature — the risk is that
  hand-written English modal→mood rules are themselves a small hardcoded inventory (the same failure mode
  as `en_morph_diff`, just a bigger one), so success should be measured the same way `affix_function.py`
  measures everything else — held-out prediction accuracy — not by rule count.

### 3.3 Subsume `en_morph_diff` rather than delete it

Once 3.1 is validated, `induce/glossing.py::en_morph_diff` becomes a special case: a same-word-family
lexical diff heuristic that only fires when the English *pivot word itself* inflects (house→houses). That
signal is real and complementary to UD-feature projection (which works off `spacy`'s morph tags on the
pivot sentence, not off comparing two induced English glosses for the same root) — the fix is not deleting
`en_morph_diff` but demoting it to a fallback that fires only when `affix_function.py`'s projection has no
opinion on that affix, matching the "generalize before enumerate" pattern already used elsewhere in this
codebase (`induce/cotrain.py`'s coverage-guarded loop is a structurally similar precedent: a cheap signal
kept as a guarded fallback, not thrown away).

### 3.4 LLM-RAG proposal for affixes that clear neither gate

For affixes `affix_function.py` cannot label (support/lift/share too low — likely most functional affixes
on the thinnest pilot languages, e.g. Gitksan-scale corpora) route them through the existing swappable LLM
endpoint (`llm-hosting-swappable-endpoint` memory) using the Jungar-Tuvan/Prompt-and-circumstance retrieval
pattern: retrieve in-context examples of the affix's context (aligned pivot words/sentences it co-occurs
with) and prompt for a candidate gloss, then require the candidate to clear the *existing* HC-verification
gate before being accepted — never trust the LLM output directly into a golden set. This is additive to,
not a replacement for, the deterministic pipeline; it should land as a proposer feeding
`review/deferrals/discover.py`'s ticket system, consistent with how LLM-touched proposals already flow
through this repo (`deferral-packages-impl` memory: LLM-live generators are explicitly a documented
follow-on, not yet built).

- **Concrete finding worth citing when scoping this**: the Jungar-Tuvan paper found providing an explicit
  morpheme *dictionary* to the LLM **hurt** accuracy for 3 of 4 models tested — so the first version of
  this should retrieve aligned *sentence/word context*, not attempt to hand the LLM a lexicon file.

### 3.5 Noise-filtering upgrades to `affix_function.py::cooccur`/`rank_functions`

Lower priority than 3.1–3.4 because the existing `LIFT_MIN`/`MIN_SUPPORT`/`MIN_SHARE` gate is a reasonable
first-pass filter and has never been run against real data yet (3.1 should come first so there's something
to tune against). Once 3.1 produces results, two specific upgrades from §1.3 are directly applicable:

- **1:1-alignment restriction** (Täckström et al. 2013): `_project_rows`/`_word_alignment` currently don't
  appear to filter alignment links by cardinality — check whether `align/aligner.py`'s output already
  guarantees 1:1 links or passes through many-to-one THOT links; if the latter, restricting to 1:1 before
  feeding `cooccur` is a cheap, well-evidenced noise reduction. (Checked `align/eflomal_vs_hmm.md`, an
  untracked file in this repo documenting a real eflomal-vs-HMM accept-rate comparison — it does not
  discuss alignment link cardinality, so this would be new analysis, not something already answered.)
- **Type-level aggregation**: `cooccur` currently tallies per-token co-occurrence directly; a Täckström-
  style intermediate step (aggregate a distribution over feature-values *per affix form* before applying
  the lift/share thresholds — which is close to, but not identical to, what `rank_functions` already does)
  is a small refactor, not a new mechanism.

---

## 4. Open questions / risks

- **Does `affix_function.py` actually produce anything on the 18 pilots, or does it fail the same way
  `en_morph_diff` does but for different reasons?** Unknown until 3.1 is run. Plausible failure modes:
  alignment starvation (already seen for Nyangbo in the pilot report), spaCy's English morphologizer simply
  not exposing enough feature granularity for languages needing fine-grained distinctions (e.g.
  evidentiality has no UD feature slot at all — `FEATURE_KEYS` cannot represent it regardless of alignment
  quality), or corpus size below the `MIN_SUPPORT=6` floor for most affixes on the thinnest languages.
- **Evidentiality and switch-reference have no home in `FEATURE_KEYS` or UD's feature inventory at all.**
  This is not a projection-quality problem, it's a representation gap — UD's morphological feature set was
  designed around Indo-European-heavy treebanking practice and doesn't have first-class slots for these
  categories the way Case/Gender/Person do. Extending `FEATURE_KEYS` for these would require either a
  non-UD feature source or heuristic detection directly in `project.py` (evidentiality in particular often
  correlates with reporting verbs/hearsay markers in the pivot prose — a periphrastic-recovery problem, see
  §3.2 — rather than a token-level morphological feature at all).
  Whether that's tractable from English pivot text specifically (English marks evidentiality
  extremely weakly, mostly lexically — "apparently," "reportedly," hedging verbs) is a genuine open
  question, not just an engineering gap; it may be one of the harder chunk types even with a working
  periphrasis-recovery layer.
- **CRF-on-gold as a parallel pilot-only path (§2 table) is architecturally attractive but unscoped.**
  Whether it's worth building a second, gold-supervised glossing subsystem for the subset of PolyGloss
  languages that have promoted golden sets — rather than pushing everything through the gold-blind
  `affix_function.py` path — needs a decision, not just a technical assessment; it changes what "the
  system" means for those languages (gold-supervised vs. gold-blind-and-scored-against-gold are different
  claims about what was learned).
- **Whether `affix_function.py`'s existing `LIFT_MIN`/`MIN_SUPPORT`/`MIN_SHARE` thresholds are well-tuned
  for the pilots' much smaller corpus sizes** (they were chosen against 8 eBible languages with far more
  data than several PolyGloss pilots) — needs empirical measurement, not assumption, once 3.1 has run.
- **LLM-RAG proposal (3.4) risk of silent quality regression**: unlike the deterministic HC-verification
  gate for segmentation, there is no equivalently strong verifier for whether an LLM-proposed *gloss label*
  is correct — HC verification confirms a parse is *structurally* consistent, not that a feature label is
  *semantically* correct. This needs the same held-out-accuracy discipline `affix_function.py` already
  applies, not a weaker bar just because the source is an LLM.
- **Per-language training-size figures disagree across sources** (see §1.1's table vs.
  `Polygloss_integration.md`'s Arapaho/Gitksan counts vs. GlossLM's implicit corpus-composition numbers).
  Different snapshots of PolyGloss/SIGMORPHON-ST data appear to be in circulation; any future benchmarking
  against these external numbers should re-derive counts from the actual HF dataset snapshot in use
  (`corpus/polygloss/fetch.py`) rather than trusting a cited figure from a paper.
- **The P17-4001 TAM-annotation tool (§1.4) was not independently verified** — its PDF did not extract
  cleanly, its author list is unconfirmed, and claims about its method are second-hand (search-result
  summaries only). Before citing it as a basis for anything beyond the current speculative mention in §3.2,
  read the actual paper and confirm authorship.
