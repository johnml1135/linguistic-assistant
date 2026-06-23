# bilingual/

The **Apertium-alignment bridge** — morphology-aware cross-lingual **reference-finding** for parallel
QA, plus **FLExTrans interop**. It is *input to QA, never translation output*: no MT, no `.t1x/.t2x/.t3x`
transfer rules, no Constraint Grammar. See the OpenSpec change `apertium-alignment-bridge` and the
[[cross-lingual-sense-link]] primitive.

## What it does

```
source lemma ──▶ bidix lookup ──▶ candidate vernacular lemma(s)
            ──▶ locate the target token whose Hermit Crab lemma matches (anywhere in the sentence)
            ──▶ Correspondence (found + position + features)  |  "missing concept"
```

Matching is on **lemma**, not surface form, so it survives word order and inflection. Deterministic:
same inputs → same result.

## Run it (offline — no Apertium binary, no HC, no network)

```bash
python research/bilingual/tests_smoke.py
```

## Modules
- `contract`/`crosswalk.py` — the versioned tag crosswalk (project POS/features ↔ Apertium `sdef`);
  unmapped tags are **reported, never dropped**.
- `stream.py` — Apertium stream format (`^surface/lemma<tag>…$`) parse/render + the **HC→stream adapter**
  (lets the vernacular side join the bidix world *through* Hermit Crab).
- `sense_links.py` — `SenseLink` (the primary `bilingual/*` datum) + `from_change_set` (reads
  `bilingual.sense_link.add` ops) + `build_bidix` (derive a bidix from links).
- `bidix.py` — in-memory bidix + Apertium `.dix` read/write + lookup. Convention: `<l>`=reference,
  `<r>`=vernacular. **Derived artifact**, never hand-edited.
- `finder.py` — the deterministic reference finder (`find_reference`, `find_all`).
- `qa.py` — deterministic *candidate* flags (`missing_concept`, `agreement_mismatch`), review-only;
  the wrong-sense / confirm judgment is the skill layer, not here.
- `flextrans.py` — import/export a FLExTrans `bilingual.dix` (bidix only; transfer rules out of scope).
- `fixtures.py` — a reordered+inflected source/target pair + toy bidix.

## Data model
**Sense links are primary** (the reviewable `bilingual/*` change-set tier; ops added to
`research/proposal/change_set.OP_TYPES`). The Apertium `.dix` is **derived** from them — the same
discipline as "the HC grammar XML is a build artifact; the change-set is the source."

## Where the Apertium binary fits (optional)
Everything here is plain Python. The native `lttoolbox`/`lt-proc` toolchain (Linux-first; WSL/Docker on
Windows) is needed **only** to use off-the-shelf reference-language analyzers (`apertium-eng`, …) or to
compile `.dix` to FSTs — its absence degrades gracefully, never breaks the core.

## Open items (see the openspec change tasks)
- Reconcile the exact FLExTrans `bilingual.dix` layout / tag direction against a real sample (6.3).
- Optional `lt-proc` integration for off-the-shelf analyzers (6.1); optional vernacular monodix export (5.2).
