# Golden set: self-validating lexicon + morphology benchmark

> **Status:** design of record, 2026-06-16. Defines the project's own "golden set" — manually-
> *constructed-but-machine-verified* lexical + morphological data, the raw data a linguist would
> decipher it from, an assessment harness that ablates the gold and scores agent proposals, and the
> packaging that makes it a harness-test / RL set. Complements [research/README.md](../../../research/README.md)
> (the harness + benchmark matrix) and [2026-06-16-runtime-and-staging-architecture-design.md](2026-06-16-runtime-and-staging-architecture-design.md).

## Purpose

The product is a FlexToolsMCP-style assistant: it investigates mono and parallel sentences and
**proposes lexemes/grammar that work** against an incomplete FLEx project. To measure that, we need a
gold set that mirrors the real task — not LingGym's multiple-choice syntax (calibration only). This
spec builds one.

The user's four requirements map onto four artifacts:

1. **Golden LibLCM-equivalent data** — verified lexicon + morphology, per language.
2. **Raw data** a linguist would analyze to produce (1).
3. **Assessments** — an agent gets (2) + an *incomplete* version of (1) and proposes the missing
   pieces; the proposal is validated.
4. **A test / RL set** — (3) packaged as a reproducible scored instance set with a reward function.

## Settled decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Anchor task** | Lexicon **and** morphology together | Morphology (Hermit Crab) is the deterministic *verifier* wrapped around the open-ended lexicon *proposal* — matches the real end-to-end app. |
| **Provenance** | Open-bootstrap first | CC-licensed published data; no community-consent gate; publishable. Converter seam lets real FLEx data drop in later. |
| **Canonical format** | **LIFT** (lexicon) + **Hermit Crab grammar XML** (morphology) | Text, git-diffable, FLEx-importable; keeps Windows-only `flexlibs`/LibLCM out of the eval loop (per project scope: emit change-sets, not DB writes). `.fwdata` round-trip is a later Tier-2 fidelity check. |
| **Correctness** | **HC-functional** (primary) + form/gloss exact-match (diagnostic) | "Lexemes that work": a proposal is correct if Hermit Crab re-parses the held-out wordforms with the gold analysis present and **without regression**. |
| **Verification** | **No human in the loop.** Opus 4.8 + layered checks. | See below — the binding certifier is deterministic + externally grounded, not Opus's opinion. |

## Verification without a human (the integrity model)

Opus 4.8 *constructs* the gold and *adversarially reviews* it, but Opus's opinion is **never** the
thing that certifies correctness — that would be circular (Opus builds gold → Opus is evaluated →
Opus judges), exactly the leakage the research backbone forbids. Certification rests on two
**independent, non-opinion** anchors, with Opus as assembler + skeptic on top:

1. **Deterministic round-trip (binding).** A gold grammar is certified only if `hc` (HermitCrab.NET)
   parses the gold wordforms, the **gold analysis is among the outputs**, and **spurious ambiguity**
   stays under a cap. This is a program's verdict, not a judgment.
2. **Cross-source agreement (binding).** Derived facts are checked against *independent* open data:
   gloss abbreviations vs the Leipzig/【gloss_reference】 set; root/affix inventories vs **UniMorph**
   paradigms and **IMTVault** IGT for the same language; language metadata vs **Glottolog**; and the
   source corpus's own prose where available. Disagreements are flagged, not silently accepted.
3. **Layered Opus review (advisory).** Independent Opus passes with *distinct lenses* (segmentation
   sanity, gloss/POS consistency, allomorph over-capture, ambiguity) adversarially try to *refute*
   each gold item. Refuted items drop out or get repaired; survivors must still pass (1) and (2).
4. **Tests (binding).** Property tests on the frozen gold: every `\m`/`\g` pair is round-trippable;
   no orphan affix; no lexical entry unreachable by any attested form; lexicon/grammar split is
   casing-consistent.

The eval/train firewall holds: a fixed gold split is reserved for evaluation and never used to
generate RL/tuning data.

## Component 1 — the golden artifact

Per language, frozen under `research/golden/<glottocode>/`:

| File | Maps to | Contents |
|---|---|---|
| `raw/igt.jsonl` | req. 2 | Agent-visible input: orthography + free translation; segmentation included only in the "easy" track. |
| `gold/lexicon.lift` | req. 1 | Verified LIFT — roots/stems, POS, gloss/sense (lowercase-glossed morphemes). |
| `gold/grammar.hcgr.xml` | req. 1 | Verified Hermit Crab grammar — affixes, natural classes, phonological rules, templates (uppercase grams). |
| `gold/analyses.jsonl` | oracle | Per-wordform gold segmentation + gloss the grammar must reproduce. |
| `meta.json` | provenance | Source, **license**, glottocode, counts, build hash, certification report. |

## Component 2 — raw data

Bootstrap source: **SIGMORPHON 2023 Interlinear Glossing Shared Task**
(`github.com/sigmorphon/2023glossingST`), per-language **CC BY-NC 4.0**. Each example has `\t`
(orthography), `\m` (segmentation), `\g` (gloss), `\l` (translation), `\p` (POS, some langs). The
*uncovered* track-2 files carry the full gloss = our gold source; track-1 (unsegmented) is the
hardest raw-input variant. Starter languages: **Lezgi, Tsez, Uspanteko**, with **Gitksan** (~31
sentences) kept as a deliberate low-resource stress case. UniMorph / IMTVault / Glottolog are
**cross-check** sources (verification), not primary inputs.

> **License caveat (record, don't ignore):** BY-NC means the *derived gold* is research-use only —
> it cannot ship inside a commercial product, and that colors RL use. The **pipeline** (ingest →
> split → certify → ablate → score) is the reusable, license-clean asset; non-NC corpora and real
> FLEx data flow through the same code.

## Component 2→1 — build pipeline (offline, per language)

1. **Ingest** the `\t/\m/\g/\l/\p` records → a common internal IGT record.
2. **Mechanical split** by Leipzig casing → candidate lexicon (lowercase meaning-glosses) +
   candidate grammar (uppercase grams, with their attested allomorphs and environments).
3. **Draft the HC grammar** (Opus, assisted by [linguistics/](../../../linguistics/) primitives &
   workflows) — natural classes, affixes, phonological rules, templates.
4. **Certify** via the four-anchor model above; iterate draft→certify until the round-trip gate and
   cross-source checks pass on a coverage threshold.
5. **Freeze**: write the five files + content hash + certification report.

## Components 3 & 4 — assessment harness + RL packaging

- **Ablator** — removes a controlled set at a chosen granularity (lexical entry / sense / allomorph /
  affix / phon-rule), emitting `(incomplete lexicon+grammar, now-unparseable held-out wordforms,
  removed items as answer key)`.
- **Instance generator** — parameterizes *what* is ablated and *how much context* is shown →
  difficulty tiers (easy: segmentation given, single gap → hard: raw text only, multiple interacting
  gaps). Each `(gold, ablation seed)` → one instance.
- **Agent interface** — instance = raw data + ablated lexicon/grammar; the agent returns **LIFT/HC
  edit ops** (a text change-set, matching project scope — no DB writes).
- **Scorer** — applies ops → runs `hc` →
  - *Primary (reward ∈ [0,1]):* fraction of held-out forms re-parsed with the gold analysis present,
    **gated on non-regression** (previously-parsed forms still parse; spurious ambiguity under cap).
  - *Diagnostics:* exact form/POS/gloss match vs removed gold; optional calibrated Opus-judge.
- **Output** — per-instance + summary JSONL mirroring `research/benchmarks/results/ab_*.jsonl`.
- **RL packaging** — the scorer is a pure `(instance, proposal) → reward` function; the same function
  serves frozen-set eval and sampled-ablation RL. `hc` is deterministic ⇒ reproducible reward. The
  eval split is never sampled for RL.

## Repo integration & the Tier-2 seam

Lives in `research/` reusing the existing `LLMClient` interface and results conventions. Because the
canonical format is LIFT + HC, real FLEx data later needs only a `.fwdata → (LIFT + HC)` extractor
(`research/data_prep/`, Windows-only, one-time) — the ablator, scorer, and harness are unchanged.

## Risks

- **BY-NC** restricts commercial/RL reuse of the *derived gold* (mitigation: pipeline is the asset;
  swap in non-NC/real-FLEx data).
- **Circularity** if Opus self-certifies (mitigation: deterministic round-trip + cross-source
  agreement are binding; Opus is advisory).
- **Casing split is heuristic** — portmanteaux (`.`-joined), clitics (`=`), multi-word glosses
  (mitigation: certification tests catch mis-splits; flag, don't silently accept).
- **Coverage is corpus-bounded** — unattested morphology is excluded from gold, not scored as
  failure.
- **Spurious ambiguity is the silent killer** — it is an explicit gated metric, not just recall.
- **HC authoring is labor-heavy** — mitigated by Opus first-draft + the round-trip gate as an
  objective stopping condition (no human bottleneck).

## Out of scope (this spec)

Parallel-translation QA gold (separate slice), real-FLEx Tier-2 ingestion, and the `.fwdata`
round-trip fidelity check — all deferred, all reachable through the same format/seam.
