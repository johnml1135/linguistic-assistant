## Context

Deferrals are produced by `propose.py` (lexical: word→gloss), `propose_morph_seg` (affix functions), and
`sense_pick`/`bootstrap` — each currently a flat `defer` record `{word, candidates, conf, aligner_top1,
current_gold}`. The gold, grammar, and parser already exist: `golden/hc.py` parses with an HC grammar built
from `LangModel` (LexEntry + allomorphs + affix rules + phon feature substrate); `parsegym/questions.py`
holds 12 scripted speaker-question archetypes with slot templates; `parsegym/schema.py` has a strict
scenario dataclass with `fix / unknown / ask_speaker` solutions; `deltas/` is a confidence-routed,
git-tracked proposal ledger with appliers. The model is reachable through `harness/` (ik_llama=Gemma,
opus, mock). This change assembles these into a reviewable, trackable resolution package.

The guiding constraint from the requester: **very formulaic / scripted**, **at least half auto-generated
from the resolution options available in HC**, and the deterministic spine must be **usable with no LLM**.

## Goals / Non-Goals

**Goals:**
- A single strict ticket schema (JSON + rendered markdown) that every deferral source emits.
- HC-grounded counterfactual parses: each hypothesis is a real grammar edit, re-parsed and diffed.
- Deterministic Phase A that builds a complete, useful ticket with **zero LLM calls**.
- Optional LLM enrichment (Phase B) and workflow escalation (Phase C) that are strictly additive and
  HC-verified — they can never inject an unparseable or unchecked claim.
- Bug-tracker lifecycle: tags, dependency ordering, status, resolution → `deltas/` write-back.

**Non-Goals:**
- A web UI (the net10 "loop console" consumes these later; here we emit JSON+md a UI/CLI renders).
- Generating translations or running MT.
- Auto-applying resolutions without human action (everything routes through the user + `deltas/`).
- Solving agglutinative segmentation perfectly; we ticket what's uncertain, not force a parse.

## Decisions

### D1. One schema, three populators (tiered)
A frozen `DeferralTicket` dataclass (mirrors `parsegym.Scenario`, adds hypotheses + counterfactuals +
resolution). Phase A populates it deterministically; Phase B/C only *add* hypotheses/prose to the same
schema. **Why:** keeps the contract stable so the bug-tracker and renderer never branch on tier.
*Alt considered:* separate schemas per tier → rejected (renderer/store churn, harder diffing).

### D2. A hypothesis IS a grammar edit; counterfactuals are HC output (automatic)
`Hypothesis = {mechanism, edit}` where `edit` is a typed op over the `LangModel` (add LexEntry, add
MoStemAllomorph, add MoInflAffMsa, add PhonologicalRule, split homograph, re-segment). The engine clones
the gold grammar, applies the edit, runs `golden/hc.py::run_parse` on the focus verse + 3–5 related verses
(selected by shared root/affix/frequency), and records `{verse, parse_now, parse_if_hypothesis}`.
**Fully deterministic, no LLM.** **Why:** this is the literal "if A were true this sentence parses like X,"
and HC is the source of truth, so the evidence is real, not narrated. *Alt:* LLM-described consequences →
rejected (unverifiable, the whole point is grounding).

### D3. The automatic ↔ LLM boundary (the core of this design)

| Step | AUTOMATIC (deterministic) | NEEDS AN LLM |
|---|---|---|
| Classify deferral `type` | yes when the source tags it (no-parse, lexeme-mismatch, unknown-affix, homograph by gold POS-count) | only for genuinely ambiguous type (Phase B fallback) |
| Enumerate hypotheses | yes — fixed HC-mechanism taxonomy per type (e.g. no-parse → {add root, allomorph of nearest lemma, stem+known-affix, new phon rule}) | hypotheses **outside** the taxonomy (novel splits, suppletion guesses) — Phase B |
| Counterfactual parses | **yes — HC**, always | never (LLM proposals are HC-verified, not HC-replaced) |
| Presentation options (5–10) | yes — select + slot-fill from `questions.py` by type/hypothesis | better phrasing / picking the most discriminating 5 — Phase B (optional) |
| Impact tag | yes — corpus frequency × wordforms a fix would newly parse | — |
| Dependencies | yes — shared-entity graph (tickets touching the same lemma/affix/stem) | — |
| Confidence tag | yes — from source conf + aligner agreement + hypothesis-score margin | — |
| Human prose (`context_md`) | a templated fallback exists | the readable narrative — Phase B |
| Hard/clustered tickets | routing is automatic (impact/dep tags) | the deeper investigation — Phase C workflow |

**Principle:** anything that can be *enumerated from HC's resolution space or computed from the corpus* is
automatic; the LLM only supplies **reach** (hypotheses/phrasings the taxonomy lacks) and **readability**,
and HC gates everything it proposes. Phase A alone yields a complete, correct ticket.

### D4. Store = JSONL now, ledger-integrated, tracker-ready
Tickets live in `deferrals/<pair>/tickets.jsonl` (git-tracked, one record/line, like the gold). Status +
tags are fields; the dependency DAG is derived. A resolution emits a `deltas/` op (confidence-routed),
so accepted answers flow to the gold through the existing applier. **Why:** reuses the proven ledger; a
SQLite/Gitea/loop-console front-end can index the JSONL later without schema change.
*Alt:* straight to GitHub issues → rejected (couples to a host; loses the typed edit + HC link).

### D5. Phase B verification gate, Phase C trigger
Phase B: a `package_builder` skill returns candidate hypotheses + prose; each hypothesis's `edit` is run
through the D2 engine and **dropped if it doesn't parse** the focus form. Phase C fires only when a ticket
is `impact:high` or sits in a dependency cluster ≥ K; it fans out one agent per mechanism (via `Workflow`)
and synthesizes. **Why:** pay model/compute cost only where it changes the outcome.

### D6. The system is a 4-stage pipeline, each an independent signal-to-noise dial
The ticket builder is one slice of a loop. Modeling it as 4 stages makes each one separately measurable
and improvable, and clarifies where errors are tolerable vs not:

| Stage | What it does | Who does it | Error tolerance |
|---|---|---|---|
| **1. Auto-accept** (low-hanging fruit) | sweep the obvious (gloss/POS) with no human | THOT ∩ light LLM high-conf | **≥99.5% precision** — flagged `ai-auto`, auditable, revertible; lexical only, no morph/phon |
| **2. Candidate selection** | pick the next-most-resolvable thing to attack | THOT output + deterministic algorithms (impact, resolvability, forms→one-lexeme clustering) | recall-oriented — missing a candidate just defers it |
| **3. Hypothesis generation** | propose candidate grammar edits | taxonomy + algorithms (Phase A); LLM for reach (Phase B) | over-generation OK — stage 4 filters |
| **4. Hypothesis assessment** | rank/accept/reject a hypothesis | HC delta + reparse + **regression check** + deterministic score + LLM verdict | must be high-precision: a wrong accept corrupts the gold |

**Why split:** stage 1 optimizes for *zero errors at high volume*; stage 2 for *not missing resolvable
things*; stage 3 for *coverage of the true fix*; stage 4 for *not accepting a damaging fix*. They have
different objectives, so they get different metrics and different test scenarios. Stage 1 is the existing
`propose.py` accept-gate hardened to 99.5%; stages 2–4 are the ticket pipeline.

### D7. Regression-aware assessment (the key quality signal)
Stage 4 SHALL NOT judge a hypothesis by "does the focus form parse now." It applies the edit, re-parses a
representative slice of the corpus, and computes **net parse delta = (forms newly parsing correctly) −
(forms that regressed: were parsing, now fail or mis-parse)**. A hypothesis is acceptable only if it fixes
the focus, has non-negative net delta, and causes no high-impact regression. **Why:** a plausible local fix
(a new affix, a broad allomorph) frequently over-generates and breaks the rest of the grammar; without the
regression count the system would happily corrupt a working gold. *Alt:* focus-only check → rejected.

### D8. Validation set by ABLATION of the verified gold (the answer key for free)
We generate hundreds of ground-truthed scenarios by removing a known item from the verified gold grammar
(a LexEntry / allomorph / affix rule / phonological rule), re-parsing to find the forms that now break, and
recording the scenario `(ablated grammar state, broken focus forms, ground_truth = removed item)`. This
exercises the whole pipeline against a known answer, per stage:
- **Stage 2**: from all currently-failing forms, does selection surface the ablated region / the right target?
- **Stage 3**: do the generated hypotheses *contain* the removed item (or an equivalent)? (recall)
- **Stage 4**: does it accept the true item, reject **decoys** (a wrong edit that fixes the focus but causes
  regressions), and report the correct net delta? (precision + regression-catch)
Scenarios are tagged by impact (removing a frequent affix → high-impact, many broken forms) and by type
(lexeme/affix/phonology/homograph), giving a balanced, language-spanning suite. The existing ParseGym
`ask_speaker` / `unknown` scenarios cover the complementary case: when the honest answer is to defer.

### D9. The grammar is noisy — hypotheses include REPAIR, not just ADD
Rules already in the grammar can be wrong (an over-broad affix, a mis-glossed lexeme, a bad allomorph).
A hypothesis SHALL therefore be any of: **add**, **narrow/condition** an existing rule, **retract** a rule,
or **split** an entry. The pipeline detects suspect rules from their footprint — a rule implicated in many
mis-parses or in the regressions of other hypotheses becomes its own ticket ("this rule looks wrong").
**Why:** in a noisy, bootstrapped grammar, the highest-value fix is often *removing* a globbing rule, not
adding another. *Alt:* additive-only → rejected (can't self-correct; error compounds).

### D10. State-aware + cyclical (not once-through)
The pipeline runs repeatedly; the right move depends on the parsing **state** (almost-nothing → lexeme
bootstrapping; mid → affixes/classes; near-complete → irregulars, phonology, edge cases). Stage-2 selection
and stage-3 generation SHALL be conditioned on state. Crucially, **resolving one ticket changes the state**,
so deferred/ticketed items SHALL be **re-evaluated**: a question that was unanswerable can become
low-hanging fruit once a dependency resolves (it may even promote to the Stage-1 auto-accept tier). The
store supports re-open/re-score; the loop iterates toward convergence (no new confident resolutions).
**Why:** the user's own point — phases are cyclical; yesterday's hard ticket is today's freebie.

### D11. Restrictiveness / the subset principle (two narrow rules vs one globbing rule)
Net parse delta is necessary but not sufficient: a broad "globbing" rule and two narrow rules can both fix
the focus with positive net delta, yet the broad one **over-generates** (will mis-parse future/held-out
forms). Stage-4 scoring SHALL add a **restrictiveness term**: prefer the hypothesis with the smallest
licensed surface set that still covers the evidence (the subset principle), measured by (a) over-generation
on held-out forms and (b) the conditioning specificity of the rule. The package SHALL, when both are viable,
**present the narrow-vs-broad choice explicitly** to the user with the trade-off (coverage vs over-generation).
Conversely, the **archiphoneme-collapse** hypothesis (see processes) is the *good* globbing: one underlying
form + a phonological rule that the data licenses, replacing a list of allomorphs — restrictiveness favors it
only when the rule round-trips with no regressions. **Why:** over-generation is the dominant failure mode of
induced grammars; restrictiveness is the linguist's Occam and must be a first-class score.

### D12. Intelligible presentation = discriminating edge cases + concrete reparse
The package SHALL show the human concrete consequences — "if A, this verse reparses as X; if B, as Y — is X
correct?" — and SHALL **select the edge cases that best discriminate the live hypotheses** (the minimal
pairs where A and B disagree), not arbitrary examples. Edge-case selection is deterministic where possible
(forms the candidate hypotheses parse differently) and LLM-assisted for phrasing the question a non-linguist
can answer. **Why:** the reviewer's accuracy depends entirely on being shown the *distinguishing* evidence,
not a wall of parses.

### D13. Linguistic processes we are currently ignoring (documented in this repo)
The hypothesis taxonomy + the unsupervised segmenter cover concatenative prefix/suffix only. The repo
already documents richer processes that the deferral pipeline must be able to hypothesize:

| Process | In repo | Pipeline gap → add |
|---|---|---|
| **Infixation** (tgl -um-, -in-) | `golden/hc.py` supports infix rules; `cycle` uses it | segmenter finds only pre/suffix → add infix discovery + infix hypothesis |
| **Reduplication** (tgl mag-RED, partial/full) | named only (`cycle/README`) | major gap → reduplication detector + HC reduplication mechanism |
| **Archiphoneme + harmony collapse** (swh applicative -ia/-ea) | **built** in `cycle/hc_phonology.py` (verified round-trip) | not a hypothesis type → "collapse allomorph family → archiphoneme + rule" (the *good* globbing of D11) |
| **Noun-class concord / agreement** (swh Bantu) | documented (`agreement`, 62 hits) | word-by-word pipeline ignores cross-word concord → use agreement as a constraint/signal + a hypothesis dimension |
| **Derivation vs inflection** (causative/applicative/nominalizer) | affix_function labels affixes | doesn't tag derivational (changes POS/valency) vs inflectional → add the distinction to affix hypotheses |
| **Compounding** (multi-root) | mentioned (`assess/inventory.py`) | not a hypothesis type → multi-root split hypothesis |
| **Apertium bidix** (2nd deterministic signal) | `apertium-alignment-bridge` change | unused → optional third concurring signal for Stage-1 / candidate evidence |

Phase A adds infix + archiphoneme-collapse (both have HC support already) and the derivation/inflection tag;
reduplication, concord, and compounding are flagged for a follow-on once their HC representation is settled.

### D14. "Which hypothesis is better" = the existing grammar-quality metrics (reuse `research/assess/`)
The repo already has the principled answer to better-rules, and this change MUST reuse it rather than
reinvent the ad-hoc "net delta + restrictiveness" of D7/D11:
- **`assess/mdl.py`** — the two-part MDL code `L(G) + L(D|G)`. A hypothesis is a grammar edit; score the
  grammar **before vs after** and compare hypotheses by **ΔMDL in bits**. This is Goldsmith's exact
  criterion and it *automatically* penalizes over-generation (ambiguity costs bits) and decides
  **split-vs-combine** — i.e. it is the rigorous form of D11's "two narrow rules vs one globbing rule."
- **`assess/metrics.py`** — coverage, spurious ambiguity, gold round-trip (boundary P/R/F1 + exact
  analysis), generalization ratio, **over-generation**, dead constructs, and **productivity (Tolerance
  Principle)** — Yang's rule: a rule is productive only if its exceptions are below the tolerance
  threshold, which is *exactly* the "add a rule vs list exceptions" decision the user raised.
- **`assess/worst_part.py`** — the per-construct ablation ranking ("what's the worst part of this
  grammar?"). This **feeds Stage-2 candidate selection** (attack the worst part next) and **D9 repair**
  (the worst construct is the suspect rule).
- **`assess-grammar` skill** + the golden non-regression gate already exist; the assessment SHALL run them.

So Stage-4 decides "A better than B" by ΔMDL + the scorecard deltas (coverage↑, ambiguity↓, over-gen↓,
productivity within tolerance), not by parse-count alone; D7's net delta and D11's restrictiveness become
*inputs/derivations* of these measures. **This change DEPENDS ON the `assess-grammar` change** (the metric
definitions are its contract) and consumes its scorecard rather than duplicating formulas.

### D15. Present the metrics intelligibly (not just a verdict)
The ticket SHALL show, per hypothesis, the metric deltas a linguist reasons about — ΔMDL (bits), coverage
gained, ambiguity added, over-generation, productivity vs tolerance, and the worst-part rank it addresses —
so the human sees *why* one hypothesis is better, alongside the concrete reparse edge cases (D12). The
verdict is the metric; the prose explains it.

### D16. Linguistic coverage ledger (the "nothing neglected" audit)
Every linguistic dimension is explicitly **covered now**, a **flagged follow-on** (needs HC/representation
work), or **out-of-scope with a reason** — nothing is silently dropped:

| Dimension | Status |
|---|---|
| Concatenative prefix/suffix, homograph split, clitic vs affix | **covered** |
| Infixation (tgl -um-/-in-) | **covered** (added; HC supports) |
| Archiphoneme + harmony collapse (the *good* globbing) | **covered** (added; reuse `cycle/hc_phonology`) |
| Derivation vs inflection tag (causative/applicative/nominalizer) | **covered** (added) |
| Suppletion / irregular stems | **covered** (allomorphy) |
| Grammar-quality metrics: MDL, coverage, spurious ambiguity, generalization, over-generation, **productivity/Tolerance**, dead constructs, worst-part | **covered** (reuse `research/assess/`; the "which is better" criterion) |
| Noisy-grammar repair (narrow/retract/split), restrictiveness, cyclical re-eval, state-awareness, edge-case presentation | **covered** (D9–D15) |
| Negative evidence ("you can't say that") | **covered** (the `grammaticality` question feeds restrictiveness) |
| Allomorph **conditioning** (MoStemAllomorph PhoneEnv — *which* allomorph when) | **follow-on** (gold uses unconditioned allomorphs today) |
| Phonological-rule **ordering / interaction** (feeding/bleeding, HC strata) | **follow-on** |
| Reduplication (tgl), noun-class **concord/agreement** (swh), compounding | **follow-on** (need HC representation; concord also usable as a cross-word constraint) |
| Audio-derived **allophony** (surface↔underlying) | **follow-on** (the `audio-evidence-addon`/allosaurus path; phonology is text-only now) |
| Valency / argument-structure change (deep effect of derivation) | **out-of-scope** (semantic/syntactic; beyond morphological parsing) |
| Tone | **out-of-scope** (the four targets are non-tonal) |

### D17. Per-language profile — constrain + configure the solution space (first-class)
Different languages make different things POSSIBLE; the search should not propose a Spanish infix or a
Swahili gender. A first-class `language_profile` per pair (`golden_sets/<pair>/profile.json`) both **prunes**
the hypothesis space and **configures** thresholds, and is itself **learnable** (features are testable
hypotheses). Contents:

- **Morphological typology** — type (isolating/agglutinative/fusional/polysynthetic) and the **allowed
  affixation processes**: prefix / suffix / infix / circumfix / **reduplication** / compounding. (spa:
  suffix-heavy, no infix/redup; tgl: infix + reduplication; swh: prefix+suffix stacking.) → gates the
  hypothesis taxonomy + the segmenter.
- **Phonological typology** — vowel harmony (y/n + type), nasal place assimilation, tone (y/n), syllable
  structure / phonotactics, the consonant **place features** needed for assimilation rules. → gates which
  phonological-rule hypotheses are even formed.
- **Morphosyntactic feature space** — which FsFeatStruc dimensions the language HAS and their value sets:
  tense/aspect/mood, person/number, **gender vs noun-class** (spa gender M/F; swh ~15 noun classes, no
  gender), case, definiteness; plus agreement/concord targets and basic word order. → bounds the features
  a hypothesis may assign (no "case" for a caseless language).
- **Orthography / writing system** — script, digraphs (sw `ng`/`ch`), diacritics, the segment inventory,
  number format. → tokenization + the phonological segment set. (Supersedes today's `meta.writing_system`.)
- **Operational config** — the **per-language auto-accept precision bar (99.5 vs 99.9)**, the **pivot
  language** (English now, not assumed), **resource flags** (has UniMorph / Wiktionary / audio?) that gate
  which sources/stages run, and the Tolerance-Principle / confidence parameters.
- **Per-feature confidence + lock + provenance** — every feature carries a confidence, a `locked` flag, and
  a source (WALS / Grambank / Glottolog / linguist / inferred-from-corpus).

**How it constrains:** a `locked` feature is a HARD prune (the disallowed rule type is never proposed,
keeping the search tractable and spurious-rule-free); an uncertain feature is a SOFT prior (deprioritized in
ranking, still allowed). **How it configures:** auto-accept reads the per-language bar; selection/generation
read the resource flags + state; assessment bounds FsFeatStruc to declared categories.

### D18. "What if this feature were different" — features are testable hypotheses
A typological feature is a hypothesis one level above rule-hypotheses, and the SAME `assess/` machinery
judges it: temporarily toggle the feature (e.g. *allow reduplication*), re-run the relevant pipeline slice,
and compare the grammar by **ΔMDL / coverage / over-generation** on the gold/corpus. If enabling it
materially improves the grammar with no regression, recommend a profile update (with the evidence);
`locked` features are never auto-flipped (they need a linguist). Profiles are **seeded from internet
typology data** (WALS/Grambank/Glottolog) where available and **reconciled with corpus evidence** — the
same "validate against internet data" discipline as the lexicon. **Why:** typological facts are also noisy;
the profile must constrain *and* be falsifiable, so a wrong "no reduplication" can be caught by the data.

## Risks / Trade-offs

- **Taxonomy too narrow (Phase A misses the real fix)** → Phase B adds out-of-taxonomy hypotheses, always
  HC-verified; the ticket still shows the user the deterministic options.
- **HC search explosion on a hypothesis grammar (timeouts)** → counterfactuals are chunked + per-verse
  timeout (existing `run_parse` behavior); a timed-out hypothesis is marked "unverified," not silently right.
- **Counterfactual over-generation (many parses)** → diff shows the targeted analysis; cap displayed parses.
- **Dependency graph wrong (bad ordering)** → it's advisory (sort hint), never blocks a user from any ticket.
- **LLM hallucinated prose** → prose is non-authoritative; the JSON hypotheses/counterfactuals are the truth.
- **Ticket volume (hundreds)** → impact-priority + dependency clustering surface the high-value few first.

## Migration Plan

1. Land Phase A (schema, counterfactual engine, builder, store, renderer, CLI) behind offline tests.
2. Backfill tickets from existing `defer` records (`propose.py` outputs) — no model needed.
3. Add Phase B enrichment (harness, gated on a live endpoint; mock in CI).
4. Add Phase C escalation (Workflow) for flagged tickets.
Rollback: tickets are additive JSONL; deleting `deferrals/` and the new modules reverts with no gold impact.

## Open Questions

- Related-verse selection for counterfactuals: shared-root vs shared-affix vs frequency — start with union, tune.
- Resolution → `deltas/` mapping for `accept_with_words` (user supplies new forms): new op or extend `set_gloss`?
- Do Phase B presentation-option rewrites need speaker-locale constraints (script/orthography) surfaced in the ticket?
