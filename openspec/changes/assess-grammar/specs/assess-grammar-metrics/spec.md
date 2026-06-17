## ADDED Requirements

Notation used below: `W` = the set of attested wordforms (types) from the corpus; `tok(w)` = token
count of `w`; `hc(w)` = the set of distinct analyses HermitCrab returns for `w`; `G` = the grammar
(lexicon + Hermit Crab morphophonology); a "construct" `c ∈ G` is one lexical entry, allomorph,
affix-process, phonological rule, natural class, or ad-hoc rule. When a golden answer key exists,
`gold(w)` = the certified analysis for `w` (see `golden-set`). All measures are computed
deterministically from `hc` output; none requires a model.

### Requirement: Parse coverage (type and token)
The scorecard SHALL report coverage as the fraction of wordforms that receive at least one analysis,
at both type and token level:
`coverage_type = |{w ∈ W : |hc(w)| ≥ 1}| / |W|` and
`coverage_token = (Σ_{w: |hc(w)|≥1} tok(w)) / (Σ_{w} tok(w))`.
Coverage SHALL NEVER be reported as a standalone quality score — it is gameable by over-generation and
MUST be presented alongside spurious ambiguity and (when available) over-generation. (Standard
parser-evaluation practice; the over-generation hazard is the SIGMORPHON-2022 segmentation precision
concern, Batsuren et al. 2022.)

#### Scenario: Coverage reported with its counter-metric
- **WHEN** the scorecard is produced
- **THEN** `coverage_type`, `coverage_token`, and `spurious_ambiguity` appear together, and coverage is
  never emitted as the sole headline number

### Requirement: Spurious ambiguity
The scorecard SHALL quantify how many analyses parsed words receive, over `P = {w ∈ W : |hc(w)| ≥ 1}`:
- `mean_analyses = (Σ_{w∈P} |hc(w)|) / |P|`
- `ambiguity_rate = |{w ∈ P : |hc(w)| > 1}| / |P|`
- `average_parse_base = exp( (Σ_{w∈P} ln |hc(w)|) / |P| )` (geometric mean; 1.0 = fully unambiguous).
Lower is better; this is the primary counter-metric to coverage. (Spurious ambiguity as a first-class
parser-quality concern — `golden-set` design "spurious ambiguity is the silent killer"; the geometric
mean is the word-level adaptation of the Average Parse Base from parser evaluation, Carroll & Briscoe
1998, "Parser Evaluation: a Survey and a New Proposal".)

#### Scenario: Ambiguity rises when an over-broad rule is added
- **WHEN** a rule that produces extra unattested analyses is added to `G`
- **THEN** `mean_analyses` and `average_parse_base` increase, flagging the regression even if coverage is unchanged

### Requirement: Gold round-trip accuracy (boundary P/R/F1 and exact-analysis)
When a golden key exists, the scorecard SHALL report, over the held-out gold wordforms:
- **Exact-analysis recall** `= |{w : gold(w) ∈ hc(w)}| / |W_gold|` — the "HC-functional" correctness of
  `golden-set` (the gold analysis is among HC's outputs).
- **Boundary precision/recall/F1** at the morph-segmentation level: with `B_pred(w)` and `B_gold(w)` the
  predicted and gold sets of segmentation boundary positions for the best-aligned analysis,
  `P = Σ|B_pred ∩ B_gold| / Σ|B_pred|`, `R = Σ|B_pred ∩ B_gold| / Σ|B_gold|`, `F1 = 2PR/(P+R)`.
(Boundary P/R/F1 is the SIGMORPHON-2022 Morpheme Segmentation Shared Task metric, Batsuren et al. 2022.)

#### Scenario: Exact-analysis recall on the golden split
- **WHEN** the grammar is scored against the golden held-out forms
- **THEN** the scorecard reports the fraction whose gold analysis appears among HC's outputs, plus boundary F1

### Requirement: Grammar size (description-length proxy)
The scorecard SHALL report the raw inventory counts of `G` — lexical entries, allomorphs,
affix-processes, phonological rules, natural classes, inflection features, strata, ad-hoc rules,
productivity restrictions — and a transparent weighted size `S = Σ_t w_t · n_t` over construct types `t`
with documented default weights. Raw counts SHALL always be shown (not only `S`); `S` is an
interpretable Occam *proxy*, with the principled objective living in `assess-grammar-mdl`. (Formal
simplicity / fewer symbols = better grammar: the evaluation metric of generative phonology, Chomsky &
Halle 1968, *SPE*; the size term of the two-part code, Goldsmith 2001.)

#### Scenario: Size counts reported per construct type
- **WHEN** the scorecard is produced
- **THEN** every construct-type count is listed individually, and the weighted size `S` with its weights is shown

### Requirement: Generalization ratio (rule vs enumeration)
Over morphemes with more than one attested surface form, the scorecard SHALL report
`generalization_ratio = (alternations derived by a phonological rule) / (total morphophonemic alternations)`,
where the denominator counts each morpheme-internal alternation once and the numerator counts those a
phonological rule derives rather than a listed allomorph. Higher = more "capture the generalization".
(Prefer one rule over many listed allomorphs: Chomsky & Halle 1968 *SPE* evaluation metric; Goldsmith
2001 rule-vs-list trade-off.)

#### Scenario: Collapsing allomorphs into a rule raises the ratio
- **WHEN** listed allomorphs are replaced by a single phonological rule over a natural class
- **THEN** `generalization_ratio` increases and grammar size counts for allomorphs decrease

### Requirement: Dead / unused constructs
The scorecard SHALL flag any construct `c` that participates in zero analyses across `W`
(`fires(c) = 0`), reporting a dead-construct list and `dead_rate_t = |{dead c of type t}| / n_t` per
type. (Pruning candidates; standard coverage/usage analysis.)

#### Scenario: A rule that never fires is flagged
- **WHEN** a phonological rule applies to no attested form
- **THEN** it appears in the dead-construct list as a removal candidate

### Requirement: Over-generation
When attested/gold data is available, the scorecard SHALL report over-generation as analyses produced
that are neither the gold analysis nor otherwise attested: over the gold held-out set,
`overgeneration_rate = (Σ_w (|hc(w)| − [gold(w) ∈ hc(w)])) / Σ_w |hc(w)|`, and SHALL report
**non-regression**: previously-parsed forms still parse and gain no new spurious analyses after an edit.
(Precision side of segmentation evaluation, Batsuren et al. 2022; non-regression gate from `golden-set`.)

#### Scenario: An edit that adds wrong analyses fails non-regression
- **WHEN** a grammar edit causes a previously-correct form to gain an extra wrong analysis
- **THEN** the non-regression check fails and over-generation rises

### Requirement: Per-construct utility — the "worst part" ranking
The scorecard SHALL rank constructs by a leave-one-out cost/benefit so the assessor can answer "what is
the worst part of the grammar". For each construct `c`, recompute the metrics on `G \ {c}` (reusing the
golden ablator) and define:
- `benefit(c) = Δcoverage_token(c) + Δexact_analysis_recall(c)` (what removing `c` loses),
- `cost(c) = size_contribution(c) + ambiguity_contribution(c)` (what `c` adds),
- `worstness_metrics(c) = λ·cost(c) − benefit(c)` with documented `λ` — **higher = worse** (high cost,
  low benefit).
Constructs are ranked **descending** by `worstness_metrics(c)`; the highest are the worst parts. This
"higher = worse" orientation deliberately matches `assess-grammar-mdl`'s `worstness_mdl(c)` so the two
rankings are directly comparable (their agreement is the consistency check in `assess-grammar-mdl`). The
recompute on `G \ {c}` SHALL reuse the leave-one-out ablation from `research/golden` (one construct
removed at a time). (Leave-one-out ablation; the marginal-description-length view of the same ranking is
in `assess-grammar-mdl`, after Goldsmith 2001.)

#### Scenario: A high-cost low-benefit rule is surfaced as worst
- **WHEN** a rule adds ambiguity and size but enables few correct parses
- **THEN** it ranks near the top of `worstness_metrics(c)` and is reported as a top "worst part"

### Requirement: Productivity (Tolerance Principle)
For a rule `R` that could apply to `N` eligible items of which `e` are exceptions, the scorecard SHALL
report `R` as **productive iff `e ≤ N / ln(N)`** (and report `e`, `N`, and the threshold). Rules failing
the test are flagged as candidates for lexicalization rather than productive generalization. (The
Tolerance Principle, Yang 2016, *The Price of Linguistic Productivity*, MIT Press.)

#### Scenario: A rule with too many exceptions is flagged non-productive
- **WHEN** `e > N / ln(N)` for rule `R`
- **THEN** `R` is reported as non-productive (lexicalize) with `e`, `N`, and `N/ln(N)` shown

#### Scenario: A rule with an undefinable eligible class is not scored
- **WHEN** the eligible-item set `N` for rule `R` cannot be unambiguously counted from `G`
- **THEN** the scorecard reports `productivity: not-computable` for `R` rather than a false pass/fail

### Requirement: Scorecard output format
The scorecard SHALL be emitted as deterministic JSON (stable key order, no timestamps) carrying every
measure above plus grammar/corpus identifiers and a content hash, comparable across runs and mirroring
`research/benchmarks/results/` conventions. The same schema SHALL be producible by the Python and the
C# (`liblcm-grammar-analyzer`) implementations.

#### Scenario: Two runs on identical inputs produce identical scorecards
- **WHEN** the scorecard is computed twice on the same grammar + corpus
- **THEN** the two JSON outputs are byte-identical
