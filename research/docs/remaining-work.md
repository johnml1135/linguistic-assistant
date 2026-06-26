# Remaining work & system audit (2026-06)

Companion to `research/README.md` and `learning_paradigms_plan.md`. Audit of where the system stands,
what to clean up, what to build next, and the spec for the throwaway Streamlit review UI.

---

## 1. Audit — how are we doing?

The system has two halves, each validated by its own golden set:

| half | what it does | output store | validated by | status |
|------|--------------|--------------|--------------|--------|
| **LEAF** | high-volume easy analysis, auto-approve | delta store | golden **RULES** (`golden_sets/`) | wired for 8; **~5% auto-approve** |
| **TRUNK** | hard structural analysis → great report → human | profiles + reports | golden **REPORTS** (`review/paradigm/golden/`) | built + measured; per-pair only |

**The honest headline: the two goldens only meet on swh.** Full end-to-end validation (rich golden rules
*and* a golden report) exists for exactly one language — so "the whole system works end to end" is an
**n=1** claim today. Everything else is one half or the other.

**Leaf reality check** (route of all 16,194 delta ops): **5% accepted · 72% review · 24% deferred.** The
leaf is wired and populated for all 8 langs, but it is *not yet* carrying the easy bulk — most ops are
mid-confidence and fall to review. Raising the auto-approve share (better confidence signals, or
golden-rules-backed auto-accept) is real leaf work, not just plumbing.

**Trunk reality check**: pipeline is built, tested (15 tests), and honestly measured. Separable metric
works (swh: detector saturated, improve Gemma; tur: Gemma saturated, improve detector). The case detector
generalizes the Bantu-only discovery layer to suffixal case (6/8 vs WALS). But: per-pair runner only (no
batch), n=1 golden per (lang,paradigm), report goldens for only swh+tur, and **no human approval step yet**
— the trunk loop is open (that's what the Streamlit UI closes, §4).

**Coverage of the two goldens (note the inverse pattern):**

| lang | golden RULES | golden REPORTS | leaf deltas | case switch |
|------|:---:|:---:|:---:|:---:|
| swh | **full** | noun-class, agreement | ✓ | absent ✓ |
| ind | full | — | ✓ | absent ✓ |
| tgl | full | — | ✓ | absent ✓ |
| spa | full | — | ✓ | absent ✓ |
| tur | thin (POS only) | **case** | ✓ | present ✓ |
| vie | thin | — | ✓ | present ✗ (over-seg) |
| hin | thin | — | ✓ | absent ✗ (analytic) |
| rus | thin | — | ✓ | present ✓ |

spa/ind/tgl have rich **rules** but no **reports**; tur has a **report** but thin **rules**. Closing that
inverse gap is the highest-leverage trunk work (§3).

---

## 2. Cleanup (prioritized)

| # | item | severity | action |
|---|------|----------|--------|
| 1 | **Delta-store split-brain** | **DONE** | Unified on `review/deltas/store/` via a single `STORE_DIR`/`store_path()` in `review/deltas/store.py`; repointed all 6 read sites (explore ×3, opus_review, cotrain, morph_align_hc) + `build_store` + `deferrals/store` default. 114 tests pass. |
| 2 | pytest config | DONE | `[tool.pytest.ini_options] python_files=tests_*.py` added — `pytest` now collects without `-o`. |
| 3 | Top README stale | DONE | rewritten to current layout + two-goldens/leaf-trunk frame. |
| 4 | 15 package READMEs stale | OPEN (MED) | `cycle/`→`induce/`, `proposal/`→`propose/`, `golden/`→`gold/`, `harness/`→`propose/harness/`. Worst titles FIXED (`induce/`, `propose/`, `gold/`). Remaining ~12 are collision-prone (`golden/` vs `golden_sets/`, "proposal" the word) → do as a careful per-file pass, not bulk sed. |
| 5 | root `deltas/` remnant | DONE | orphaned 804-byte swh stub `git rm`'d after the repoint left it with no readers. |
| 6 | `induce/morph_align.py` | none | marked superseded by `align/morph_align_hc.py` but still used as the offline fallback — keep, leave the docstring note. |

---

## 3. Roadmap (build next, in leverage order)

**Trunk (highest leverage):**
1. **Batch runner** — DONE (`review/paradigm/sweep.py`): walks unlocked paradigms with the progressive
   cascade, scores against goldens, records onto profiles. Current snapshot: 29 paradigms, 4 scored, 13
   locked, 11 no-builder, 1 generated.
2. **Report goldens for the langs that already run a packet but lack a golden.** DONE: rus case (honest
   0.33 after the role-aware fix) and **spa gender-number** (1.0 — third detector family: gender via
   determiner agreement -o→el/-a→la, number via -s; 8/8 vs WALS, switch-gated so tgl case-markers / vie
   noise don't false-positive). The cross-check now meets on **4 languages** (swh/spa/tur/rus). Next cheap
   wins (the sweep marks them "generated" — packet runs, no golden):
   - DONE: **voice-focus** (ind di-, 0.5), **analytic np-case** (tgl ang/ng/sa, 1.0), **TAM** (swh
     na/li/ta/me/ka, 1.0), **possessive/number** (tur -lAr 0.5, rus -ов 0.5). **7 detector families**,
     10 scored anchors across 6 langs (mean 0.65), 211 tests pass.
   - Remaining detector gaps: **hin postpositional case** (Devanagari ने/को/से fragment; auto-side picks
     preceding demonstratives — needs Devanagari-aware tokenization + force following-side); **vie
     isolating-confirm** (the inducer over-segments isolating vie, confounding both synthesis and the
     isolating check — needs the induction fix first); **rus fusional** case+number (declension-table
     detector + suffix→cell-mapping scorer to get past 0.33/0.5).
3. **Scorer: marker-overlap over-credits fusional morphology** — PARTLY DONE. Completeness is now
   **role-aware** (`Cell.match_roles` + `score._cell_present`): a golden case-cell counts only if a packet
   family has the marker AND a matching projected role. This dropped fusional rus from a fake 0.5 to an
   honest 0.33 (nom + instr) and keeps tur genuine. STILL OPEN: a true declension-table detector for
   fusional case (one ending → multiple case×gender×number cells), and a suffix→case *mapping* check
   beyond role compatibility.
   Also DONE: **detector determinism** — case vote tallies are disk-cached per (lang, sample)
   (`review/paradigm/.cache/`, gitignored), so the metric is reproducible across processes (THOT
   alignment is otherwise stochastic) and fast. `case_votes(..., refresh=True)` recomputes.
4. **≥3 goldens per (lang,paradigm)** + average ≥3 LLM samples — n=1 + single-sample overfits; LLM scores
   are run-variable. Independently verify the swh noun-class 1.0 (authored after seeing the packet = ceiling).
5. **Detector improvements the metric now measures:** tur oblique-case separation; vie over-segmentation
   (inducer invents affixes in an isolating lang → wrong synthesis switch → vie.isolating-confirm locked);
   an **analytic/adposition** case detector for hin (postpositional, not suffixal).
6. **Live frontier number:** `ANTHROPIC_API_KEY` for an `opus`-as-generator run (client already fixed).

**Leaf:**
6. Raise auto-approve share above 5% — use golden-RULES agreement as an auto-accept signal (an op that
   matches the oracle is safe to accept), and tune the confidence composition. Surface the review queue in
   the UI so the 72% review tier becomes actionable.

**Backbone:**
7. Fill golden **rules** for tur/vie/hin/rus (currently POS-only) so the leaf has a backdrop to validate
   against for the diverse langs.

---

## 4. Streamlit review UI (throwaway) — the trunk's missing approval half

The trunk currently *generates* reports but has **no approval step** — the loop is open. "Show me the
reports, let me query the data, let me say 'yes, this is true'" **is** the trunk's human-in-the-loop
approval. The write-back is the center of the design, not a viewer afterthought.

**Stack:** Streamlit, local, throwaway (Stage-1 host; the real host is the C# loop console later). Reads
the existing artifacts; writes approvals back through the existing functions — no new data model.

**Three views:**
1. **Reports** — pick (lang, paradigm); show the generated `ParadigmReport` (cells, conditioning, fit_none,
   prose, evidence citations) **side-by-side with the golden** and the score breakdown (completeness ×
   faithfulness, missing-from-packet, hallucinated). Source: `review/paradigm/run.py` / `profiles/<lang>.json`.
2. **Query the data** — the reviewer interrogates evidence: regex → words + glosses
   (`review/reviewer_query.py`), browse every noun with class signals (`review/explore.noun_entries`),
   the A/B/C+fit hypotheses (`explore.class_hypotheses` / `case_detect.case_hypotheses`), and the leaf
   review queue (delta store ops in the `review` tier).
3. **Approve** — "yes, this is true" buttons that write back:
   - on a trunk report → `profiles.record_result(status="confirmed")` (and optionally lock the underlying
     leaf deltas via the store `decision(accept)`).
   - on a leaf delta in the review tier → `DeltaStore.decision(sig, accept)` (locks it).

**Open decision before building approve (don't auto-resolve):** *is "golden" the ceiling or the approved?*
The user defined golden reports as "the best we can generate" (a ceiling); a human approving a *generated*
report means "good enough," which is different. **Approve must NOT auto-write the golden set** — that would
collapse the ceiling into the floor and the metric would stop meaning "how close to best." Promoting an
approved report into the golden set must be a separate, deliberate action. Resolve this when building.

**Prereq:** fix the delta-store split-brain (#1) first — the UI's leaf queue must read the populated store,
not the stale root stub.
