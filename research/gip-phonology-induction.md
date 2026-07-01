# Phonology-Induction Gap: State of the Art & a Path Off Hand-Authored `HARMONY_CLASSES`

Research pass informing `induce/phonology.py`'s Phase 1 archiphoneme collapse. The concrete gap: `HARMONY_CLASSES`
(`induce/phonology.py:25-33`) has exactly one hand-authored entry (Swahili height harmony), so `propose_archiphoneme()`
(`induce/phonology.py:79`) is dead code for every one of the 18 PolyGloss pilot languages (Arapaho, Tsez, Lezgian,
Ainu, Ruuli, Vera'a, Natügu, Cayuga, Japhug, Beja, Dolgan, Kamas, Selkup, N‖ng, Mauwake, Kalamang, Basque, Nyangbo —
see `Polygloss_integration.md` §6.2) even though `induce/tdd.py::harmony_families()` groups their allomorphs into
suspected-harmony families just fine (0-46 `enumeration_debt` per language, all currently un-collapsible). This doc
surveys the actual state of the art for proposing the missing natural class automatically, and recommends where to
spend effort first.

---

## 1. State of the art

### 1.1 Automatic natural class discovery / distinctive feature induction

**The core algorithm is old, not new, and is a search, not a learning problem.** Given a set of segments known to
pattern together, Chomsky & Halle's SPE (1968) formulation — restated cleanly in Hayes' *Introductory Phonology*
(2009, ch. 4, `https://www.ling.upenn.edu/~gene/courses/530/readings/Hayes2009_ch4.pdf`) — defines the natural class
of a segment set as the (possibly non-unique) smallest conjunction of feature-value pairs that (a) every member of
the set satisfies and (b) no segment *outside* the set, drawn from the relevant language's phoneme inventory,
satisfies. This is a bounded combinatorial search (try feature-value conjunctions of increasing size, e.g. up to 3-4
features, over a small inventory of ~5-40 candidate feature dimensions) — not a statistical/ML problem once you have
(i) a feature table for the segments and (ii) the reference inventory to search within. There is no single canonical
open-source implementation of this exact minimality search that we found (Hayes distributes a pedagogical
"Brackets"/feature-chart page, not packaged software), but the algorithm itself is mechanical enough to implement
directly against a feature table — see §3.1.

**The empirical ceiling is real and load-bearing for how much to trust any auto-proposed class.** Mielke, *The
Emergence of Distinctive Features* (Oxford, 2008) ran the natural-class search described above against 6,077
attested phonological-process target/trigger classes drawn from 628 language varieties, scored against three
standard feature theories (Preliminaries to Speech Analysis, SPE, Unified Feature Theory). **No single theory
characterizes more than 71% of the attested classes; over 24% are not characterizable in *any* of the three
theories.** "Unnatural" classes are not rare outliers — frequency-ranking classes gives a smooth curve with no
natural/unnatural boundary. Implication: an automated proposer that returns "no coherent class found" for ~25-30% of
real harmony families is not a bug, it is matching the linguistic literature's own finding, and the pipeline's
`collapsible=False` retain-with-reason path (already present in `propose_archiphoneme()`) is the correct response,
not a shortfall to eliminate.

**Feature-vector data sources**, all IPA-input:
- **PanPhon** (Mortensen et al., COLING 2016, `https://github.com/dmort27/panphon`, `pip install panphon`) — a CSV
  database mapping ~5,000+ IPA segments (base + diacritic-augmented) to 22-24 articulatory feature values
  (`+`/`-`/`0`), plus a `FeatureTable` Python class (`word_fts()`, `word_to_vector_list()`, `word_array()`) and a
  `Segment`/`Distance` API (Hamming/weighted feature-edit-distance, "Dolgo Prime" equivalence-class distance).
  Confirmed via GitHub README fetch: **no orthography-to-IPA conversion, and no built-in minimal-natural-class
  search** — both would need to be built on top.
- **CLTS / SoundVectors** (List et al., part of the CLDF/lexibank ecosystem, `https://calc.hypotheses.org/7224`) — a
  generative alternative to PanPhon's fixed lookup table: derives a 39-feature vector from an IPA string's own
  descriptor (handles unseen sounds, contour tones, diphthongs, consonant clusters) rather than requiring the sound
  to already be in a database. Same IPA-in requirement as PanPhon.
- **PHOIBLE 2.0** (Moran & McCloy, `https://phoible.org`) — 3,020 phoneme inventories, 2,186 distinct languages
  (glottocode-indexed), each phoneme annotated with distinctive features. Distributed as CLDF (plain CSV:
  `inventories.csv`, `values.csv`, ...), readable with stdlib `csv` or `pycldf` — no heavy dependency required. This
  is the right source for "what is language X's actual phoneme inventory" (the search space for §1.1's minimality
  algorithm), separate from PanPhon's universal cross-linguistic segment table. Caveat: some glottocodes have
  multiple divergent inventories from different source descriptions — don't blind-average them.

### 1.2 Unsupervised/weakly-supervised phonological alternation & rule learning

- **Albright & Hayes' Minimal Generalization Learner** (MGL; Albright & Hayes 2003, *Cognition* 90; tool page
  `http://www.mit.edu/~albright/mgl/`) — given a set of input→output word-form pairs (e.g. lemma→inflected form),
  builds a specific rule per pair, then iteratively merges pairs of rules into their "minimal generalization" (the
  most specific rule that subsumes both), scoring each resulting rule by type-frequency reliability. Designed
  originally for English past tense but is alternation-agnostic — it operates over phonological-feature-annotated
  segments, so in principle applies to any Input→Output alternation set, including harmony allomorph pairs. Typical
  published applications use hundreds to low-thousands of paradigm pairs (English past tense ~4,000 verb types);
  we found no published lower-bound test at the 500-2,000-*sentence*-corpus scale this project operates at, and MGL
  assumes phonologically-annotated (feature-vector) input, not raw orthography.
- **Goldsmith's Linguistica** (Goldsmith 2001 *Computational Linguistics* "Unsupervised learning of the morphology of
  a natural language"; Linguistica 5, open-source, `https://aclanthology.org/J01-2001.pdf`,
  `http://people.cs.uchicago.edu/~jagoldsm/`) — MDL-guided unsupervised morphology induction from raw text alone
  (no prior lexicon), later extended (Goldsmith & Xanthos, "Learning phonological categories") to unsupervised
  acquisition of morphophonological *categories* (proto-natural-classes) as a downstream step once morphology is
  segmented. Directly analogous in spirit to this repo's induce→generalize pipeline shape (segment first, generalize
  the residue second), though Linguistica's phonological-category step is less developed/maintained than its
  morphology component and we could not confirm it is still actively packaged for feature-based harmony collapse
  specifically.
- **Optimality Theory constraint-ranking learners** — Tesar & Smolensky's Constraint Demotion / Error-Driven
  Constraint Demotion (*Learnability in Optimality Theory*, MIT Press 2000) learn a total ranking of a *given*
  constraint set from positive input-output pairs, converging in at most N(N-1)/2 informative pairs for N
  constraints; Boersma & Hayes' Gradual Learning Algorithm is the stochastic-ranking variant. **These are ranking
  learners, not constraint/feature *inventors*** — they presuppose the natural-class-based constraints already
  exist (e.g. "Agree[height]"), which is exactly the piece this project is missing. Not directly applicable without
  first solving §1.1.
- **Hayes & Wilson's MaxEnt Phonotactic Learner** (*Linguistic Inquiry* 39, 2008,
  `https://brucehayes.org/papers/HayesAndWilsonPhonotactics2008.pdf`) is the one classical system that *does*
  induce its own constraints (not just rank given ones): starting from an SPE-style feature set and positive-only
  word data, it greedily searches short feature-conjunction "windows" (single features and small conjunctions) for
  ones that are significantly under-attested, and weights the resulting constraint set by maximum entropy. This is
  the closest classical precedent to "search over feature conjunctions to explain an observed alternation
  automatically" — the search procedure (small feature-conjunction enumeration, scored by fit) is a reusable
  template even though the paper's target is phonotactic well-formedness, not harmony conditioning specifically.
- **Calamaro & Jarosz** ("Learning General Phonological Rules From Distributional Information," *Cognitive Science*
  2015, `https://onlinelibrary.wiley.com/doi/10.1111/cogs.12167`) extend an earlier allophony-distribution learner to
  alternations involving contrastive segments and to generalizing beyond individual segment pairs into rule-level
  statements. Cognitively-motivated (models child acquisition), operates over phonologically-transcribed corpora;
  we could not directly verify its minimum-data convergence point from the abstract alone (full text access limited
  in this pass) — flagged as unverified in §4.

### 1.3 Automatic harmony-dimension detection specifically (the exact missing step)

This is the most direct hit for the actual gap — "given surface allomorphs alone, which phonological dimension
(height/backness/rounding/place/voicing) is conditioning the alternation":

- **Adam C. Baker, "Two Statistical Approaches to Finding Vowel Harmony"** (U Chicago TR-2009-03,
  `https://newtraell.cs.uchicago.edu/files/tr_authentic/TR-2009-03.pdf`) is the most on-point precedent. Two HMM/
  distributional methods correctly detect the *presence* of harmony in Finnish and Turkish and correctly report
  *no* harmony in English/Italian, working from corpus word-form data (transcribed, not necessarily IPA-feature
  annotated) rather than a pre-given feature theory. Reported difficulty: the HMM models transparent neutral vowels
  (Finnish) easily but struggles with Turkish's secondary rounding harmony. Critically, this line of work groups
  vowels into harmonic classes **by their distributional co-occurrence behavior in the corpus itself**, not by
  looking up a phonetic feature table — i.e. it is evidence that the harmony-conditioning class can be recovered
  *without* IPA/PanPhon at all, purely from which vowels pattern together across stem/affix boundaries in the
  language's own orthographic wordforms. This is the version most compatible with this repo's no-IPA constraint
  (§2), though it identifies "these vowels group together," not automatically *which* named feature caused it
  (height vs. backness vs. rounding still needs a feature-table lookup as a labeling step *after* the grouping).
- **Steuer, List, Abdullah & Klakow, "Information-Theoretic Characterization of Vowel Harmony: A Cross-Linguistic
  Study on Word Lists"** (SIGTYP 2023, `https://arxiv.org/abs/2308.04885`) — defines an information-theoretic
  harmonicity score from vowel predictability, estimated with a phoneme-level language model (a small neural LM
  over IPA phoneme sequences). Key numbers confirmed by direct fetch: trained on **word lists of up to 1,000 entries
  per language** — comfortably inside this project's smallest corpora — and the neural PLMs still recover harmony
  patterns at that scale. Two caveats for this repo: (a) it needs phoneme-level (IPA) input, not orthography, and
  (b) per the abstract, it measures *how harmonic* a lexicon is (a strength/predictability score), not *which*
  feature dimension is doing the conditioning — it would need to be paired with a per-feature ablation (rerun with
  each candidate feature "checked out") to localize the dimension, which the paper does not appear to do itself
  (unverified from abstract-level access; full-text extraction was not possible in this pass, flagged in §4).
- **Caplan & Kodner, "The Acquisition of Vowel Harmony from Simple Local Statistics"**
  (`https://escholarship.org/uc/item/0p72d9c0`) — a local-bigram-statistics account that automatically detects
  harmony and its gross characteristics in some languages without prior feature knowledge, in the same spirit as
  Baker's work above. Authorship confirmed via search; we could not extract full-text content in this pass (PDF
  text-layer extraction failed in this environment), so treat the method details as located-but-unverified pending a
  follow-up read.
- **2024 acoustic/neural work exists but is out of scope here.** Barman, Mahanta & Sharma's "Unsupervised modeling
  of vowel harmony using WaveGAN" (SpeechProsody 2024) and "Deciphering Assamese Vowel Harmony with Featural
  InfoWaveGAN" (Interspeech 2024) are the most recent (2024) ML approaches specifically targeting vowel-harmony
  discovery. Both take raw **audio** as input and use GAN-based representation learning to surface harmony-relevant
  clusters. Considered and ruled out for this repo on two independent grounds: (a) GPU/GAN training directly
  violates the no-torch/no-GPU constraint, and (b) they require acoustic recordings, not orthographic text — this
  project's phonology-induction Phase 1 is explicitly text-only (`induce/phonology.py`'s own docstring: "no audio
  ... are required to propose or verify a collapse"), with audio reserved as a later *confirmation* signal per the
  `phonology-induction-plan` memory, not a Phase-1 input.
- No 2024-2026 work was found that solves *dimension identification* end-to-end from raw orthographic allomorph
  lists the way this project would need — the SIGTYP line needs IPA, the Baker/Caplan-Kodner line identifies the
  grouping but not automatically the feature name, and the 2024 GAN line needs audio. **This is a genuine,
  currently-open engineering gap, not just an unimplemented-but-solved technique** — see §3 for how far existing
  pieces can be assembled toward it.

### 1.4 Open-source phonetic feature tooling for a Python pipeline

| Tool | Input | Output | Deps | Orthography handling |
|---|---|---|---|---|
| **PanPhon** | IPA string | feature vector / edit distance | pure Python + CSV, no torch | none — IPA only |
| **CLTS/SoundVectors** | IPA string (any valid transcription, incl. unseen sounds) | 39-feature vector | pure Python | none — IPA only |
| **PHOIBLE** (CLDF/CSV) | glottocode lookup | phoneme inventory + features for that language | stdlib `csv` or `pycldf` | none — gives the inventory, not a grapheme mapping |
| **Epitran** (Mortensen et al., LREC 2018, `https://github.com/dmort27/epitran`) | orthographic word + language-script code | IPA/X-SAMPA string | pure Python, per-language rule files | **This is the orthography→IPA step** — rule-based G2P via greedy grapheme maps + context-sensitive rewrite rules, built specifically for extending to low-resource languages by hand-authoring new map files |

**Directly verified epitran coverage gap (checked against the repo's actual GitHub tree, not secondhand):** Epitran
ships **126** language-script map files. Of this project's **current 8** eBible targets (swh/ind/tgl/spa/tur/rus/
hin/vie), **all 8** have a ready-made map (`swa-Latn`, `ind-Latn`, `tgl-Latn`, `spa-Latn`, `tur-Latn`, `rus-Cyrl`,
`hin-Deva`, `vie-Latn`). Of the **18 new PolyGloss pilot languages**, only **Lezgian (`lez`) — 1 of 18** has a
ready-made map; Arapaho, Tsez, Ainu, Ruuli, Vera'a, Natügu, Cayuga, Japhug, Beja, Dolgan, Kamas, Selkup, N‖ng,
Mauwake, Kalamang, Basque, and Nyangbo do not. This is exactly the set of languages where `HARMONY_CLASSES` is
currently empty and enumeration debt is nonzero — the orthography→IPA blocker and the missing-natural-class blocker
land on the same languages.

---

## 2. Applicability to this codebase

Constraints, stated plainly against what §1 found:

- **No torch/GPU.** PanPhon, CLTS, Epitran, and the SPE-style minimality search are all pure-Python/CSV — fine. The
  SIGTYP phoneme-LM approach (§1.3) is a small neural LM but not necessarily torch-dependent in principle (could be
  an n-gram/count-based LM instead, which is what Baker's HMM approach already is) — if pursued, it should be
  reimplemented as an n-gram/HMM, not adopted with its original neural implementation, to stay inside the repo's
  no-torch rule (`research/README.md`).
- **Orthography, not IPA, is the native format.** `induce/tdd.py::harmony_families()` groups by literal orthographic
  characters (`_HARMONY_VOWELS = set("aeiouáéíóú")`, `induce/tdd.py:67` — itself hardcoded to Latin-script vowels
  with Spanish accents, which would fail the same way on the current 8 languages' non-Latin members — e.g. Russian
  Cyrillic and Hindi Devanagari — the same way it would on Dolgan/Kamas/Selkup Cyrillic in the new 18; not run/
  confirmed in this pass, but a direct reading of the hardcoded character set). Every feature-vector tool in
  §1.1/§1.4 requires IPA input. Epitran is the only bridge, and per the directly-measured coverage table above, it
  covers the 8 languages that already work and almost none of the 18 that need this feature most. **Practically:
  the IPA-feature route is usable today only for a minority of target languages**, and extending it means either
  (a) hand-authoring new Epitran map files per language (real linguistic labor, not a script) or (b) finding another
  G2P source per language.
- **Must work on 500-37,000-sentence corpora.** The one number we could directly confirm compatible with this range
  is SIGTYP's ≤1,000-word-list convergence (§1.3) — reassuring for volume, but that system needs IPA (the blocker
  above) and doesn't localize the conditioning dimension. Baker's distributional/HMM approach (§1.3) is the one
  precedent that avoids the IPA blocker entirely, at the cost of only grouping vowels distributionally rather than
  naming the responsible feature — but no published minimum-corpus-size number was found for it; the repo's own
  affix-form counts per family (2-6 members typically, per `induce/phonology.py`'s existing families) are far too
  small to run an HMM over directly — Baker's method needs sentence/word-level *distributional* co-occurrence data
  (which stem vowels co-occur with which affix vowels across the whole corpus), not just the small enumerated
  family list `induce/tdd.py::harmony_families()` currently hands off. That reframes the input needed: not "cluster
  these 2-6 strings," but "compute a stem-vowel × affix-vowel contingency table over every parsed word in the
  corpus," which the existing HC-parsed word stream (already read by `review/allomorph.py` per
  `allomorph-detector` memory) could plausibly supply.
- **`HARMONY_CLASSES`'s shape (`dict[str, dict[str, set[str]]]`, symbol → set of surface chars) is workable as a
  target shape for an auto-proposer**, with one addition needed: a proposer needs to emit *both* the class (a
  `set[str]`) *and* a phonetically-meaningful symbol/label (currently always hand-chosen, e.g. `"E"`/`"O"`) — an
  automated version can keep the symbol arbitrary (e.g. `"class_0"`) since `propose_archiphoneme()` only uses the
  symbol as a template character, not a meaningful name; the human-readable feature label (e.g. "front unrounded
  mid/high vowels") is a nice-to-have annotation for the dossier/report layer, not required by the collapse
  mechanics itself. No shape change to `HARMONY_CLASSES` is required to consume an auto-proposed class — only a
  new producer function is needed.

---

## 3. Recommended paths to investigate

Ranked by (evidence strength × how little new infrastructure it needs), each tied to a concrete file/function.

### 3.1 (Highest confidence, least new infra) Orthography-native distributional class discovery — extend `harmony_families()`'s output, no IPA needed

Implement Baker's core idea (§1.3) directly against this repo's own corpus, skipping IPA entirely: for each language,
build a contingency table of (stem's last harmony-relevant vowel) × (chosen affix allomorph's vowel) across every
HC-parsed word the corpus produces (the same parsed stream `review/allomorph.py` already walks). Cluster affix
vowels that have statistically similar stem-vowel co-occurrence distributions (e.g. via mutual information or a
simple confusion-matrix hierarchical clustering, no ML framework needed — this is a few dozen lines of counting +
`scipy`-free clustering, or even just eyeballing a small contingency table given how few vowels most inventories
have). **First experiment**: run this against the pilot's harmony families with the highest `enumeration_debt`
(Arapaho, Ainu, Cayuga — pick from the per-language debt numbers already computed in the pilot run) and check
whether the discovered vowel groupings match what `propose_archiphoneme()` would need (i.e. do the family's observed
vowels fall inside one discovered cluster?). This produces the *grouping* half of a `HARMONY_CLASSES` entry directly
from orthography; it does not produce a feature *name* for the class (see §3.2 for that half), which is fine because
`propose_archiphoneme()` doesn't need the name, only the set.

### 3.2 (Medium confidence, moderate new infra) PanPhon-backed natural-class labeling, gated by Epitran coverage

For the ~1-9 languages where Epitran has (or can cheaply get) a map (currently just Lezgian among the 18; Basque is
a plausible next win given it's a well-documented isolate with existing G2P resources elsewhere), implement the SPE
minimality search from §1.1 directly against PanPhon feature vectors: given a harmony family's vowel set (already
converted to IPA via Epitran), enumerate feature-value conjunctions of size 1-3 over PanPhon's 22-24 features,
keep the smallest conjunction whose extension over the language's PHOIBLE-listed inventory equals the observed set
(or the smallest superset, matching `propose_archiphoneme()`'s existing `_class_for()` semantics at
`induce/phonology.py:71-76`, which already does "smallest class that is a superset" — the missing piece is just
*generating candidate classes* instead of only matching against the one hand-typed Swahili entry). **First
experiment**: take Swahili's existing hand-authored `E`/`O` classes, run them through Epitran (`swa-Latn` map
exists) → PanPhon, and confirm the automated search recovers the same two classes independently — a clean
ground-truth check before trusting the method on a new language. Expect it to fail gracefully (à la Mielke's finding)
on some families — that is the expected, correct outcome, not a bug to chase.

### 3.3 (Lower confidence, cheapest to try, needs a verification harness) LLM-proposed natural class, symbolically verified

Consistent with this repo's existing "LLM proposes, symbolic layer verifies" pattern (`opus-as-reviewer` /
`llm_propose.py` per memory), prompt the swappable LLM client with a harmony family's members (and, if available,
Epitran/PanPhon feature glosses for context) and ask it to propose a natural class description in prose/feature
terms; then verify the proposal the same way `propose_archiphoneme()` already verifies hand-authored classes —
`expand_archiphoneme()` must regenerate every observed member (`induce/phonology.py:112-113`'s existing coverage
check is exactly the right oracle, unmodified). This sidesteps both the orthography→IPA blocker (the LLM can often
reason about a language's vowel system from its name/family even without a formal G2P table, though this is
unverified and risks silent errors — see §4) and the "which feature is responsible" localization gap that neither
§1.3 method solves cleanly. LINGOLY/PhonologyBench-style benchmarks (§1.3 note) suggest current frontier LLMs
(Claude Opus scoring best on LINGOLY's olympiad-style linguistic puzzles) are decent but not reliable at this kind of
task raw — reinforcing that the symbolic regenerate-and-check oracle must remain the actual gate, exactly as the
module's docstring already states ("the same engine+oracle discipline as the HC gate"). **First experiment**: run
this against 2-3 of the pilot languages with the highest enumeration debt and measure what fraction of LLM-proposed
classes pass the existing `expand_archiphoneme()` coverage check versus fail it — a cheap way to get a real
precision number before investing further.

### 3.4 (Exploratory, not recommended to start with) Full phoneme-level LM harmonicity scoring

Steuer et al.'s approach (§1.3) is the most rigorously cross-linguistically validated (their own SIGTYP eval), but
requires IPA input (same Epitran-coverage blocker as §3.2) and only scores *whether* harmony is present/how strong,
not which dimension — it would need to be paired with §3.1 or §3.2 to actually produce a `HARMONY_CLASSES` entry.
Worth revisiting only after Epitran coverage is deliberately extended to more of the 18 (a real linguistic-labor
decision, not scoped here), and even then this measures corpus-wide harmonicity, not per-family classes — better
suited as a corroborating a-priori check ("does this language look harmonic at all before proposing rules")
than as the class-proposing mechanism itself.

---

## 4. Open questions / risks

- **Does orthography→IPA conversion introduce more error than it resolves for languages without a phonemic
  inventory reference?** Epitran's rule-based G2P is designed for well-documented orthographies; for a language
  where the only source is one grammar description (as most of the 18 pilot languages are, per
  `Polygloss_integration.md`'s provenance notes on ODIN/IMTVault), hand-authoring a new Epitran map risks encoding
  the *linguist-author's* transcription choices as if they were a general orthography rule, silently baking noise
  into every downstream feature lookup. Not verified either way in this pass — a real risk, not a solved problem.
- **Calamaro & Jarosz's and the Nazarov/Pater-style papers' full-text content could not be verified in this pass**
  (PDF text-layer extraction failed for both, `poppler-utils`/pdftoppm unavailable in this environment) — their
  citations above rest on abstract/secondary-source text only. Before building on either, do a direct read.
- **Steuer et al. (SIGTYP 2023)'s claim of *not* localizing the conditioning dimension is inferred from the abstract
  and partial fetch, not confirmed by reading the method section in full** — worth a direct check before ruling it
  out as a §3 building block, since if it *does* support a per-feature ablation this would upgrade it from §3.4 to a
  stronger candidate.
- **Mielke's 71%-ceiling finding means any auto-proposer, however good, has a real, literature-documented failure
  rate on real languages** — the right target for a first implementation is "correctly propose classes for the
  cases that are genuinely natural, and correctly say 'no coherent class' for the rest," not 100% collapse of all
  `enumeration_debt`. Treating high residual debt after auto-proposal as a failure would be measuring against the
  wrong bar.
- **No published work was found that solves this exact problem (auto-propose which single phonological *dimension*
  conditions an alternation, from surface allomorphs alone, at 500-2,000-sentence scale, from orthography) as one
  system.** Every method in §1.3 solves part of it. This is a genuine assembly/engineering task, not a
  known-technique lookup — treat §3's ranking as a build order for original glue code, not a "which library to
  `pip install`" decision.
- **`_HARMONY_VOWELS`'s Latin-script hardcoding (`induce/tdd.py:67`) is upstream of this whole problem** and, by
  direct reading of the code (not run/confirmed against real output in this pass), would affect even the current 8
  languages the same way (Cyrillic Russian, Devanagari Hindi would silently fail the vowel-skeleton grouping,
  independent of anything in this doc) — worth flagging as a prerequisite bug, not part of the phonology-
  induction research gap per se, but blocking any script-agnostic version of §3.1 from working beyond Latin script.
