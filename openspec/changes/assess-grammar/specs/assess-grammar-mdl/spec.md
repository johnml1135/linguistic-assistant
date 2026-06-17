## ADDED Requirements

This capability operationalizes Occam's razor as **Minimum Description Length (MDL)**: of two grammars
that fit the data, prefer the one whose grammar-plus-data encodes in fewer bits. It is the principled
form of the `assess-grammar-metrics` size + ambiguity proxies, and it is the engine for the
"better?"/"split or combine?" decisions. Foundational sources: Rissanen 1978 (MDL); Goldsmith 2001
(*Linguistica* — MDL applied to morphology); Creutz & Lagus 2007 (Morfessor — MDL as MAP); de Marcken
1996 (MDL lexicon induction). Notation as in `assess-grammar-metrics`.

### Requirement: Two-part description-length objective
The module SHALL score a grammar by the two-part code
`DL(G, D) = L(G) + L(D | G)` (bits), where `L(G)` is the cost to transmit the grammar and `L(D | G)` is
the cost to transmit the corpus `D` once the receiver has `G`. A lower `DL` is better. The objective and
its two terms SHALL be reported separately so the size/fit trade-off is visible. (Rissanen 1978; the
two-part code as applied to morphology, Goldsmith 2001 §2; Morfessor's MAP form `−log p(G) − log
p(D|G)`, Creutz & Lagus 2007.)

#### Scenario: DL reported as two terms
- **WHEN** a grammar is scored
- **THEN** `L(G)`, `L(D|G)`, and `DL = L(G)+L(D|G)` are reported in bits, separately and summed

### Requirement: Grammar cost L(G) — explicit, documented encoding
`L(G)` SHALL be computed from a single documented encoding scheme covering: the morpheme lexicon
(per morpheme, `length · log2|Σ|` bits for its phonological string over alphabet `Σ`, plus list/pointer
overhead), the phonological rules and affix-processes (a per-rule structural cost), natural classes,
and features. The chosen coding SHALL be stated in the implementation and treated as an **estimator**
(MDL results are coding-dependent); changing the coding SHALL be a documented, versioned decision. The
exact coding is **deferred to implementation (task 3.1)** — documented in code with a version tag and
worked examples — and `DL` values SHALL be compared only within a single coding version.
(Lexicon-length coding after Goldsmith 2001 §2 and de Marcken 1996; Morfessor's prior over the lexicon,
Creutz & Lagus 2007.)

#### Scenario: Adding a redundant allomorph raises L(G)
- **WHEN** an allomorph that no rule needs is added to the lexicon
- **THEN** `L(G)` increases by that allomorph's encoded length plus pointer overhead

### Requirement: Data cost L(D | G) — analysis selection and ambiguity
`L(D | G)` SHALL be the cost of encoding each corpus token's analysis given `G`. Under a unigram morph
model with morph probabilities `p(m)` estimated from analysed counts, the explicit nested form is
`L(D|G) = Σ_{tokens w} [ ( Σ_{m ∈ analysis(w)} −log2 p(m) ) + log2 |hc(w)| ]` — the inner sum is the
morphs of `w`'s chosen analysis, and the per-token `log2 |hc(w)|` term (uniform over the analyses `G`
permits for `w`) pays to disambiguate them, so **spurious ambiguity is charged automatically**. (Negative-log-likelihood data cost, Goldsmith 2001 §2; Morfessor
likelihood term, Creutz & Lagus 2007; ambiguity-as-cost is the information-theoretic reading of the
spurious-ambiguity metric.)

#### Scenario: Over-generation increases L(D|G)
- **WHEN** an edit makes many tokens ambiguous without improving fit
- **THEN** the `log2|hc(w)|` disambiguation term raises `L(D|G)`, so `DL` rises even if coverage rose

### Requirement: Model-selection decisions (better? split or combine?)
The module SHALL decide between grammar variants by description length: variant `G'` is preferred over
`G` iff `DL(G', D) < DL(G, D)`. This SHALL drive the canonical edits — **merge** two morphemes,
**split** one morpheme/affix into two, or **rule induction** (positing a phonological rule in place of
listed allomorphs) — each accepted only if it lowers `DL`. (These mirror *Linguistica*'s MDL-evaluated
heuristics — morpheme merge/split and rule induction; Goldsmith 2001.)

#### Scenario: Split-vs-combine resolved by ΔDL
- **WHEN** the assessor asks whether two affixes should be one morpheme or two
- **THEN** the module computes `DL` for the merged and the split grammars and recommends the lower, reporting `ΔDL`

### Requirement: Per-construct marginal DL (worst part, MDL view)
The module SHALL rank constructs by marginal description length. Define `worstness_mdl(c) = −ΔDL(c) =
DL(G, D) − DL(G \ {c}, D)` — **higher = worse** (removing `c` saves bits, i.e. `c` costs more to specify
than it saves in data cost; equivalently `ΔDL(c) < 0`). Constructs are ranked descending by
`worstness_mdl(c)`. This matches the "higher = worse" orientation of `assess-grammar-metrics`'
`worstness_metrics(c)`, and **"agree in direction" SHALL mean a positive rank correlation** (e.g.
Spearman ρ > 0) between `worstness_mdl(c)` and `worstness_metrics(c)` on the golden set (verified in
task 6.3). (Marginal two-part cost, Goldsmith 2001.)

#### Scenario: A construct that lowers DL when removed is flagged
- **WHEN** removing `c` lowers total bits (`worstness_mdl(c) > 0`)
- **THEN** `c` is reported as a worst part in the MDL ranking, and its rank correlates positively with the metrics ranking
