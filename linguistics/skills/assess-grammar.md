# assess-grammar

> Judge grammar *quality* — "what's the worst part?", "is solution A or B better?", "should these be
> split or combined?" — from deterministic measures, and gate any refactor on the golden set. This is
> the **Refactor** judgment of the grammar-building TDD cycle.

**Judgment type:** decide + verify  ·  **Grounded in:** MDL (Rissanen 1978; Goldsmith 2001;
Morfessor/Creutz & Lagus 2007); SPE evaluation metric; Yang 2016 (Tolerance); Dressler 1987
(naturalness)  ·  **Used by:** [[../meta-workflows/steady-state-virtuous-cycle]] (Refactor),
[[../meta-workflows/test-a-grammar-theory]], [[../meta-workflows/close-the-zero-parse-loop]] (hand-off)

## The judgment

After the data parses (TDD **Green**), there are usually several *workable* grammars and not all are
equally good. This skill picks the better one and finds the weakest part to improve next — never by
opinion, always from the deterministic assessment tools, with the golden gate binding.

It answers exactly three questions, each from a tool:

| Question | Tool (in `research/assess/`) | How to read it |
|---|---|---|
| **What's the worst part?** | `worst_part.worst_part_ranking` (Approach A) **and** `mdl.worstness_mdl_ranking` (Approach B) | the highest-`worstness` constructs (low benefit, high cost / removing them lowers `DL`). Trust where the two agree (`mdl.spearman` > 0). |
| **Is A or B better?** | `mdl.description_length(...)["DL"]` + `mdl.better_grammar({...})` | lower total bits wins. The metric **scorecard** (`metrics.py`) is the supporting evidence. |
| **Split or combine?** | `mdl.decide_split_or_combine(dl_combined, dl_split)` | build both `LangModel` variants, score each, pick the lower `DL` (Goldsmith/*Linguistica*'s merge/split move). |

## Heuristic / procedure

```
1. Produce the scorecard (research/assess/builders.assess_hermitcrab → coverage, spurious ambiguity,
   gold round-trip, size, generalization, dead constructs, productivity, description_length).
2. Worst part?  -> rank by worstness; act on constructs both rankings agree are worst
                   (dead constructs and high-ambiguity/low-benefit rules first).
3. Better / split-or-combine?  -> build the candidate grammar(s); compare DL (mdl.better_grammar /
   decide_split_or_combine). Over-generation is charged automatically by the log2|hc(w)| term.
4. Tie (DL within tolerance AND equal worstness rank)?  -> break it with the naturalness rubric:
   transparency, iconicity, bi-uniqueness, productivity (Tolerance Principle e ≤ N/ln N), feature-
   defined natural classes over arbitrary lists. Naturalness is explanatory; DL wins when it separates.
5. GATE every recommended refactor: emit it as a change-set, re-run the golden round-trip
   (golden/hc.round_trip) — previously-correct forms still parse, no new spurious analyses, recall not
   reduced — and confirm spurious ambiguity did not rise. A coverage drop is allowed ONLY if DL drops.
```

## Inputs → outputs

- **In:** a grammar (`golden.LangModel` now; LibLCM later), the corpus, the golden set; for "better/
  split-or-combine", the candidate variant(s).
- **Out:** a ranked list of worst parts with their figures; a better/split-or-combine recommendation
  with `ΔDL`; and, for any recommended refactor, a gate verdict (accepted / rejected-by-gate). Each
  finding cites the numbers it rests on.

## Interaction with other skills & the gate

Consumes what [[generalize-not-enumerate]] proposes (the merge/rule move *is* the common refactor) and
is bound by [[read-the-gate]] (the golden non-regression verdict is the only "accepted" signal). Feeds
the Refactor step of [[../meta-workflows/steady-state-virtuous-cycle]] and the compare step of
[[../meta-workflows/test-a-grammar-theory]].

## Failure modes / guardrails

- **Merging on elegance.** A simpler/lower-`L(G)` grammar that regresses the golden set must be
  rejected — `DL` *and* the gate, not beauty.
- **Trusting one ranking.** Act where Approach A and B agree (`spearman > 0`); investigate where they
  diverge rather than trusting either alone.
- **Cross-version `DL` comparison.** `DL` is comparable only within one `mdl.ENCODING_VERSION`.
- **Opinion verdicts.** The prose may vary by model/run; the verdict must trace to the scorecard, `DL`,
  and gate. Never report "B is better" without `DL(A)`, `DL(B)`, and the gate result.

## Training basis

MDL model selection (Goldsmith 2001; Rissanen 1978; Creutz & Lagus 2007; de Marcken 1996); SPE
evaluation metric (Chomsky & Halle 1968); Tolerance Principle (Yang 2016); Natural Morphology
(Dressler et al. 1987); spurious-ambiguity / Average Parse Base (Carroll & Briscoe 1998). See
[../References.md](../References.md) §11 (and §2–3, §9). Implemented in `research/assess/`
(`metrics.py`, `mdl.py`, `worst_part.py`); spec `openspec/changes/assess-grammar/`.
