# Runtime & staging architecture

> **Status:** design of record, 2026-06-16. Captures the *runtime/deployment and code-maturity*
> layer of the project. The *data/engine/change-set* layer is in [README.md](../../../README.md)
> (Hermit Crab engine, two-tier change-sets, git-not-CRDT, golden-set gate). This document does
> **not** revisit those decisions; it adds the layer above them: where code lives, how it matures,
> where the LLM runs, and the first thing we build.

> **Scope note (2026-06-16):** the product is **QA + language documentation, not translation**.
> Translation is a separate fine-tuned NLLB-200 model (SIL's Serval); this tool *checks* translations
> and *documents* the language. **Apertium / transfer-rule generation is ruled out, not deferred.**
> **Aligned parallel text is a first-class input from v1**, and evaluation uses two gold sets —
> deterministic monolingual `word→gloss` (Hermit Crab) and LLM-judgment **parallel QA**
> (precision/recall). See README "Scope" and "Parallel data and two kinds of gold set".

## Three orthogonal axes (don't conflate them)

The project now has three architectural axes that are easy to mix up:

| Axis | Question it answers | Values |
|---|---|---|
| **Data / two-plane** (already in README) | Who owns the truth, who imports it | Authoring/truth plane (this repo, git) ⇄ FLEx sync plane (separate effort) |
| **Maturity / three-stage** (this doc) | How an idea matures into a product | Python research → C# validation + sample UI → product split-off |
| **Runtime / offline-online** (this doc) | What needs connectivity | Offline half (parse, review, gate, apply) ⇄ online half (LLM proposal) |

## The core reframe

The differentiator is the **judgment/skills layer**, which wants a *frontier* LLM. But a large
share of users are **offline for weeks**, and the local models that *can* run offline (7–13B) are
weakest at exactly morphology/agreement reasoning — so "run a small model in the field" guts the
thing that justifies the project.

Resolution: **the LLM is not co-located with the user.** Split the loop so the only step that needs
connectivity is the *creative proposal* step. Everything safety-critical runs locally:

```
   OFFLINE HALF (field laptop, no GPU, no internet)      ONLINE HALF (wherever compute is)
   ────────────────────────────────────────────────      ───────────────────────────────────
   • HC parse of corpus  → issue backlog                  • skills + RAG generate change-set
   • REVIEW of proposals (human; speaker or linguist)       PROPOSALS
   • apply approved deltas                          ⇄     • swappable endpoint:
   • golden-set parse+generate REGRESSION GATE              BYOK frontier | SIL-hosted | big local
   • git history of grammar + lexicon                     • batch over the backlog
```

Hermit Crab is managed .NET and needs no GPU, so the **oracle and the golden-set gate are offline
assets** — the verification/safety story never depends on the cloud.

## The three maturity stages

This repo holds stages 1 and 2. Stage 3 splits off.

1. **Research playground (Python, `research/`).** Where ideas are iterated: prompt/skill
   experiments, RAG strategies, data exploration, evaluation. Lives **in this repo**. An idea is
   "proven" when it reliably emits valid change-sets that pass the golden gate.
2. **Validation program (C#/.NET, `src/`).** The subject of this design. Builds and validates HC
   rules, makes the LLM calls, runs the parser, produces and applies change-sets, and ships a
   **sample UI** (the loop console below). The pipeline is "proven" when the loop closes
   measurably — unparsed words reduced without golden-set regressions.
3. **Product split-off (separate / downstream).** The proven C# **core** becomes a NuGet package or
   is migrated into an official product (FieldWorks, FieldWorks Lite, or Paratext 10). This is what
   customers see. The **sample UI is not part of this** — it is throwaway scaffolding; only the
   engine libraries migrate.

**Stage boundaries are promotion gates, not just folders.** Stage 1→2: a skill earns promotion by
producing valid change-sets that pass the golden gate. Stage 2→3: the pipeline earns promotion when
the loop closes measurably on a real language.

### Cross-stage contracts

Two artifacts are the seams the pipeline flows through, so they are versioned and treated as
contracts:

- **The change-set schema** — the contract *out* of stage 2 (to the FLEx-ingestion effort) and the
  lingua franca that lets stage-1 Python emit something stage 2 can validate and apply.
- **Portable skills** (markdown + explicit tool contracts) — the contract *in* from stage 1. A skill
  proven in the playground moves to the C# proposer as *data*, not a rewrite. This is the point of
  "portable skills."

## Slice 1 — the local "loop console" (the thing we build first)

A single .NET process (`dotnet run`) that serves a small web UI at `localhost` (browser or thin
webview — the FwLite pattern). It is a **control panel for the offline half plus the one online
proposal call**, driven end-to-end from the UI. **First user: the linguist-developer** (you),
proving the loop on one language — optimize for density and control, not hand-holding.

```
┌────────────────────────── one .NET (net10.0) process ──────────────────────────────────────┐
│  browser/webview ──HTTP──▶ ASP.NET Core minimal-API host ── serves ──▶ thin web UI          │
│                                   │                                                          │
│        ┌──────────────────────────┼───────────────────────────────┐                         │
│        ▼                          ▼                                ▼                         │
│   HcAdapter                 LlmProposer                     ChangeSetStore                   │
│   (SIL.Machine HC)      (Microsoft.Extensions.AI            (validate · write · apply ·      │
│   parse→backlog,         IChatClient + portable skills)      validate-and-repair)            │
│   golden parse+gen       backlog item + RAG → ops                                            │
│        ↑ local, no GPU        │ ⚠ ONLY online call               ↑ local                     │
│        └───────────────┬──────┴───────────────────┬─────────────┘                           │
│                        ▼                           ▼                                          │
│         git working dir: HC grammar XML · lexicon · corpus · golden set ·                    │
│                          issue backlog · change-set files   (git = history/undo/audit)       │
└──────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                  ⚠ online seam ────┘──▶ LLM endpoint (BYOK frontier now; SIL-hosted later, by config)
```

### Module boundaries — packable libraries + throwaway host

What migrates to stage 3 is the core, never the host. So the boundary is the whole point of stage 2.
All target **`net10.0`** (the TFM FwLite already uses, so the libraries can later be referenced
in-process by an FwLite panel or a Paratext plugin).

| Project | Does | Depends on | UI? LLM? Web? |
|---|---|---|---|
| `SIL.LinguisticAssistant.HermitCrab` | parse corpus → backlog; golden-set parse **and** generate; dangling-ref / strata checks | `SIL.Machine` | none |
| `SIL.LinguisticAssistant.ChangeSets` | change-set schema; validate · apply · validate-and-repair (incl. HC's silently-skipped rule ids) | files only | none |
| `SIL.LinguisticAssistant.Proposer` | backlog item + RAG context + portable skill → change-set ops | `Microsoft.Extensions.AI`, ChangeSets | LLM via injected `IChatClient` |
| `SIL.LinguisticAssistant.Console` *(host)* | minimal-API + thin web UI; orchestrates the three above | all three | **throwaway** |

Each library answers cleanly: *what it does / how you call it / what it depends on*; none depends on
the host. Migration to stage 3 is "give these libraries a different front end," not a rewrite.

### One cycle (driven from the UI)

1. **Scan** — HC runs over the corpus locally **and** parallel-derived checks run over the aligned
   text → one prioritized backlog combining unparsed words and parallel flags (missing sense,
   number/agreement mismatch), by frequency/impact. *Offline.*
2. **Propose** — top-N issues + RAG context through a portable skill to the LLM endpoint → `lexical/*`
   and `morphophonology/*` ops, each with rationale / confidence / impact / provenance. *Only online step.*
3. **Review** — UI shows each op with its evidence; approve / edit / reject. *Offline.*
4. **Gate** — on approve, apply ops to a *candidate* grammar; run validate-and-repair + **both** gold
   sets: the deterministic `word→gloss` parse-and-generate regression test and the parallel-QA eval
   (precision/recall on flags). *Offline.*
5. **Commit** — UI shows *failures resolved vs regressions introduced* (and QA-eval movement); commit
   to git or revert. Regressions block commit unless explicitly overridden. *Offline.*

### LLM endpoint

`Microsoft.Extensions.AI` `IChatClient`, injected. For Slice 1 it points at a **BYOK frontier**
provider (a connected dev setting). Swapping to a **SIL-hosted** open model (Serval-style) later is a
config change. Default for the shipped product is the SIL-hosted endpoint; frontier-BYOK is the
opt-in connected mode. Use batch + prompt-caching of the shared grammar/typology context when on a
batch-capable provider. **Data egress is explicit, visible config** — sending a community's corpus
to a third party is a data-sovereignty decision, not an accident of which endpoint is set.

### Error handling

- **No connectivity at step 2** → surface clearly and (Slice 1) fail/retry gracefully. This is the
  exact seam where the deferred job-queue subsystem will later plug in (queue out, proposals back).
- **Malformed ops from the LLM** → schema validation rejects; show raw + error; never apply.
- **Gate finds regressions** → block commit; show the diff; require explicit override.
- **HC silently loads a broken grammar** → validate-and-repair catches dangling/skipped rule refs
  *before* the gate. "It loaded fine" is not evidence of correctness.

### Testing

- Unit: `HcAdapter` against a tiny fixture grammar; `ChangeSetStore` apply/repair; schema validation.
- Integration: the **golden-set parse-and-generate gate** is the integration test, already in the loop.
- `Proposer` tested with a fake/recorded `IChatClient` — tests never hit a live API.

### Repository layout

```
research/        # stage 1 — Python playground (proven ideas promote out via the contracts)
src/             # stage 2 — C# net10.0: HermitCrab · ChangeSets · Proposer · Console (host)
contracts/       # change-set schema (cross-stage, versioned)
skills/          # portable skills (markdown + tool contracts; promoted from research/)
docs/            # this design and others
sample-data/     # fixture grammar/lexicon/corpus/golden-set for dev (real language data is input, not committed)
```

Note: real language data (a FLEx export) is **input**, produced outside the core loop (stage-1 Python
may use flexlibs to export it); the core loop never takes a runtime dependency on a FLEx install.

## Explicitly deferred (YAGNI for Slice 1)

- **Job-queue sync** to a SIL-hosted batch worker (offline outbox/inbox; *not* a CRDT — idempotent
  job queue). The step-2 seam is designed for it.
- **SIL-hosted endpoint** — only the swappable abstraction now; BYOK-frontier in dev.
- **Native-speaker accessibility mode** — Slice 1 is linguist-developer only.
- **CRDT / LexBox lexical sync** — lexical tier only, later (per README).
- **Multi-language and skill promotion** — prove the loop on one language first.
- **Embedding into FwLite / Avalonia / Paratext 10** — that is stage 3; the libraries are shaped for it.

### Ruled out (not deferred)

- **Machine translation / generating target text** — handled by the separate fine-tuned NLLB-200
  model (Serval). Not a future slice here.
- **Apertium / transfer-rule generation (FLExTrans-style)** — evaluated 2026-06-16 and rejected:
  it is MT machinery, and FieldWorks does not even store Apertium data (it is external to LibLCM).
  Our agreement/structure checks instead ride on the gold source structure of parallel text.

## Open questions / unknowns

- **"FieldWorks Avalonia"** — no public trace found (2026-06-16); SIL's public modernization is
  **FwLite** (.NET 10 MAUI + Blazor WebView + embedded ASP.NET Core, offline-first, lexicon-only,
  no plugin framework). Whether an Avalonia effort exists internally is unconfirmed. Either way, the
  stage-3 target is a .NET host, which is why the libraries target `net10.0`.
- **SIL-hosted fit** — whether **Serval** (self-hostable NLP REST + batch, GPU via ClearML) and the
  forthcoming **Lynx** ("framework for integrating AI tools into translation software") are the rail
  to ride for hosting/integration, rather than a parallel stack. To confirm before stage 3.
- **Skill portability under weaker models** — whether skills authored against a frontier model hold
  up when pointed at a SIL-hosted/local one. The golden gate bounds the risk but does not eliminate it.
