# Linguistics

Core linguistic reference material for this repo. This is **domain knowledge**, not code — it
grounds the skills, change-set schema, and QA checks in real morphology, lexicography, and the
FieldWorks / LibLCM data model.

It relies heavily on **SIL sources** (FieldWorks/FLEx documentation, LibLCM, Hermit Crab, Rapid Word
Collection) plus the standard linguistics literature.

## Contents

- **[References.md](References.md)** — annotated bibliography: morphology, phonology, field
  linguistics, lexicography, computational morphology, glossing standards, and the SIL/FieldWorks
  tooling docs. Every primitive/workflow cites back to it.
- **[primitives/](primitives/)** — one file per **morphological or lexical idea expressible in
  LibLCM** (the atoms: entry, sense, allomorph, MSA, affix template, phonological rule, …). Each maps
  the concept → LibLCM class → Hermit Crab → our change-set ops → QA relevance. See
  [primitives/README.md](primitives/README.md) for the index and the file template.
- **[workflows/](workflows/)** — one file per **linguistic workflow** this repo assists
  (interlinearization, parser setup, lexeme/sense building, RWC, spell-checking, dictionary
  publishing, parallel-translation QA, …). Each describes the human process, how the assistant
  supports it, the primitives involved, and the oracle/metrics. Workflows carry a **mode**
  (investigate / change). See [workflows/README.md](workflows/README.md).
- **[skills/](skills/)** — the **judgment layer** (the differentiator): reusable *judgment verbs* the
  assistant applies — propose-from-evidence, **generalize-not-enumerate**, divide-senses, guess/ask/
  defer, prioritize, read-the-gate — each grounded in how field linguists are trained. See
  [skills/README.md](skills/README.md).
- **[meta-workflows/](meta-workflows/)** — **playbooks** that sequence workflows (driven by skills)
  toward a goal: the steady-state virtuous cycle, bootstrap-a-new-language, the zero-parse loop,
  theory-testing, lexicon-building. See [meta-workflows/README.md](meta-workflows/README.md).

### The four-layer model

**Primitives** (data atoms) → **workflows** (tasks) → **skills** (judgment) → **meta-workflows**
(playbooks). A meta-workflow sequences workflows; a workflow is carried out by skills; skills read and
write primitives. The skills layer is what makes this more than a fixed parser.

## How this connects to the rest of the repo

- **Scope** ([../README.md](../README.md)): QA + documentation, not translation; morphology via
  Hermit Crab; parallel-aware checking core. The primitives/workflows here are the concrete surface
  of that scope.
- **Change-sets**: primitives say which `lexical/*` or `morphophonology/*` operation expresses an
  edit to that concept; workflows say which ops a task emits.
- **Engine+oracle principle**: each workflow names its gold/metric — the deterministic Hermit Crab
  `word→gloss` golden set and/or the parallel-QA eval.

> Status: research/exploration. Content here is reviewed against SIL sources but should be treated as
> a working reference, not authority — cite the primary SIL docs in `References.md` for anything load-bearing.
