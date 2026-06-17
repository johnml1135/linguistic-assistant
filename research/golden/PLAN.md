# Golden-set implementation plan

Spec: [docs/superpowers/specs/2026-06-16-golden-set-design.md](../../docs/superpowers/specs/2026-06-16-golden-set-design.md)

Build order. Each phase ends green (a test or a runnable artifact) before the next.

| # | Phase | Output | Depends on |
|---|---|---|---|
| 0 | **Scaffold** | `research/golden/` package, README, `.gitignore` for `_sources/` | — |
| 1 | **Ingest** | `igt.py` parses SIGMORPHON `\t/\m/\g/\l/\p` → `IGTRecord`; tests | 0 |
| 2 | **Split** | `split.py` aligns `\m`↔`\g`, casing-splits lexical vs grammatical; candidate lexicon + affix inventory | 1 |
| 3 | **HC verifier** | `hc_runner.py` wraps `hc.exe` (roll-forward); writes config+script, parses analyses; round-trip + ambiguity metrics | schema research |
| 4 | **HC emitter** | `hc_emit.py` builds HermitCrab XML from candidate lexicon+affixes | 2, 3 |
| 5 | **LIFT emitter** | `lift_emit.py` builds LIFT from candidate lexicon | 2 |
| 6 | **Certify** | `certify.py` runs the four anchors (round-trip, cross-source, Opus-review, tests); iterate to threshold | 3,4,5 |
| 7 | **Freeze** | `research/golden/<glottocode>/` gold files + `meta.json` + cert report | 6 |
| 8 | **Ablate** | `ablate.py` removes entry/sense/allomorph/affix/rule → instances | 7 |
| 9 | **Score** | `score.py` pure `(instance, proposal)->reward` via `hc`; JSONL results | 8 |
| 10 | **Agent eval** | run Opus over instances; report; mirror `benchmarks/results/` | 9 |

**Languages:** Lezgi first (clean agglutinative), then Tsez, Uspanteko; Gitksan as low-resource
stress case.

**Verifier runtime:** `hc` (sil.machine.hcparser, .NET) with `DOTNET_ROLL_FORWARD=LatestMajor`.
Proven recipe: one symbolic `seg` feature with a unique symbol per orthographic char (so HC does
exact string segmentation, no phonological merging), an `any` SegmentNaturalClass, roots as
`<LexicalEntry>`, affixes as `<MorphologicalRule>` whose `MorphologicalInput` is a
`PhoneticSequence` containing `OptionalSegmentSequence min="1" max="-1"` over `SimpleContext
naturalClass="any"` (matches an arbitrary stem); `MorphologicalOutput` = `CopyFromInput` +
`InsertSegments` (suffix) or `InsertSegments` + `CopyFromInput` (prefix). Affix POS constraints
omitted in v1 to maximize parseability; POS lives in the lexicon for diagnostics.

**v1 wordform = underlying form** (concatenation of `\m` morphemes), NOT the raw surface `\t`.
Lezgi/Tsez have morphophonology (`\t кайла` ≠ `\m кун-й-ла`), so v1 verifies morpheme+gloss identity
on the segmented underlying string; surface→underlying **phonological rules are Tier-2 enrichment**.

**Status:** verifier+emitter recipe proven end-to-end (`_scratch/`); building package (phases 0–4).
