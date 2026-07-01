# Review UI plan — Streamlit (throwaway, local)

A **task tracker** over the paradigm pipeline, with fancy reports, queries, and "what-if" tests. It shows
every paradigm × language as a task moving through the lifecycle; for each you see the generated report,
the golden, **what Opus-as-Reviewer thought (per-cell comments) and decided**, and the scores — and you
can run non-destructive "what if this were done?" hypotheses before approving.

Throwaway Stage-1 host (the real host is the C# loop console later). It READS the existing JSON artifacts
and CALLS the existing Python functions — no business logic lives in the UI.

---

## 1. The mental model

The 33 paradigms × 8 languages are **tasks** in a lifecycle:
`locked → candidate → learned → confirmed` (or `absent` = "correctly found nothing").

Each task carries: a generated **report** (cells, conditioning, residue, prose), the **golden** (ceiling),
a **score** (completeness × faithfulness), and an **Opus-as-Reviewer verdict** (per-cell promote/defer/
reject **+ a comment**, and an overall recommendation). The UI is how a human reads those and acts.

Two kinds of decisions already in the system that the UI surfaces:
- **Trunk** (per paradigm): the report's Opus verdict + the profile status (confirmed/…).
- **Leaf** (per delta op): the delta store's confidence routing — accept / review / defer.

---

## 2. What it reads — and the one thing we must add

| artifact | has it? | used for |
|----------|:--:|----------|
| `profiles/<lang>.json` | ✅ | task status + metric summary + review recommendation (the board) |
| `golden/<lang>_<paradigm>.json` | ✅ | the ceiling, shown beside the generated report |
| delta store `review/deltas/store/<lang>.deltas.jsonl` | ✅ | leaf decisions (accept/review/defer queue) |
| sweep snapshot (`sweep.py`) | ✅ (on demand) | system-wide board refresh |
| **runs store** `review/paradigm/runs/<lang>_<paradigm>.json` | ❌ **NEW** | the full generated report + score breakdown + **Opus per-cell comments/decisions** + packet summary + endpoint + timestamp |
| **decisions log** `review/paradigm/decisions.jsonl` | ❌ **NEW** | append-only human actions (approve/reject/promote, who-less/when/what) — "decisions already made" trail |

**Two ways to have content — and they cost differently:**
- **Lazy run on click** — Report detail calls `run.run(lang, paradigm)` live. Heuristic is instant
  (detectors are disk-cached), so you can *see any report* with **no backfill at all**. This is the v1
  default and means basic viewing needs nothing persisted.
- **Runs store + history** — needed for the **decisions / audit trail** ("all decisions already made"),
  NOT for viewing a report. So persistence is about the log, which de-risks phase 1.

Note: on first launch nothing has been persisted (every prior sweep ran `--endpoint heuristic` and saved
only metric summaries). Lazy-run gives instant content; a one-time backfill sweep (with persistence on)
populates the history — and its endpoint is the same choice as Q5.

### Small engine changes (prereq, ~half a day)
1. `run.py`: also write `runs/<lang>_<paradigm>.json` = `{report, score, review:{verdicts:[{cell,decision,why}], recommendation}, packet_summary, endpoint, ts}`; append the prior run to a `history` list.
2. `decisions.jsonl`: a tiny appender called on every human approve/reject/promote.
3. Stamp `ts` from the caller (scripts can't call `Date.now()`; the app passes it).

---

## 3. Views (Streamlit multipage app)

### 3.1 Board — the task tracker (home)
- Grid: **rows = 8 languages**, **columns = paradigm families** (noun-class, concord, case, np-case,
  gender-number, voice, tam, possessive, isolating, …). Each cell is a chip colored by **status**
  (locked / candidate / learned / confirmed / absent) showing the **score** (e.g. `0.83`) and the Opus
  **recommendation** (✓ promote / ~ review / ✗ reject).
- Top strip: counts (scored / locked / no-builder / generated), **mean overall**, per-status totals.
- Filters: language, layer (switches/inventory/agreement/exceptions), status, "needs review."
- Buttons: **Refresh** (re-read profiles), **Run sweep** (recompute all, spinner), **Run one** (pick).
- Click a cell → Report detail.

### 3.2 Report detail — the fancy report (per language × paradigm)
- **Header**: status, overall / completeness / faithfulness, recommendation, endpoint, run timestamp.
- **Generated vs Golden**, side by side: cells table (label · markers · function · support), conditioning,
  fit-none/residue, and the prose narrative for each.
- **Score breakdown**: cells present-in-packet, **missing-from-packet** (detector gap), **in-packet-not-
  reported** (generator gap), **hallucinated** — the separable diagnostic.
- **Reviewer panel** (the headline ask): a row per cell — `decision` (promote/defer/reject) and the `why`
  **comment**; plus the overall recommendation. **Honesty requirement (see §7 Q5):** label the panel with
  *which* reviewer produced it — the offline default `why` strings are **heuristic template output**
  ("backed by packet evidence (support=0, share=0.83)"), NOT a language model. A real LLM review (the
  firewall reviewer) must be run explicitly; show the model name + that it's heuristic-vs-LLM so the panel
  never misrepresents a template as "what Opus thought."
- **Evidence packet** (collapsible): the THOT/HC/explorer evidence the report was built from.
- **Actions**: Re-run (endpoint = heuristic / local-Gemma / opus), **Approve**, **Reject/Defer**,
  **Promote to golden** (separate, guarded — see §4). History of prior runs/decisions for this task.

### 3.3 What-if — the hypothesis sandbox (non-destructive)
"What if this were done?" Pick a task, set overrides, **Run hypothesis**, see BEFORE → AFTER. Nothing is
written unless you then click **Apply**.
- **Cell overrides**: include / exclude specific cells (e.g. "what if we drop the noisy -e gender class?").
- **Generator swap**: heuristic vs local-Gemma vs opus → faithfulness delta. *(cheap — just re-call.)*
- **Detector knobs** *(follow-on, not v1)*: per-paradigm sliders (case `purity`/`min_stems`, tam
  `min_prob`, np-case side, sample). These need the params threaded through `build_X_packet`→`detect_X`,
  which the builders don't accept yet — real plumbing, so v1 what-if = **cell-toggle + generator-swap**
  (both already answer "what if this cell weren't there / a better model ran"); detector-knobs are a
  budgeted follow-on.
- **Output**: side-by-side baseline vs hypothesis — score deltas, cells gained/lost, new Opus verdicts —
  mirroring the existing `reviewer_query` before / option-A / option-B / fit-neither stats.
- Rule-level what-if (homograph/allomorph options) via `reviewer_query.whatif` where relevant.

### 3.4 Query / Explore — interrogate the evidence
- **Regex → words + glosses** (`reviewer_query.query_words`): "show me every word matching `…ni$` and its gloss."
- **Browse entries** (`explore.noun_entries`): every noun with its class signals (prefix/class/source/conf/freq).
- **A/B/C + fit-none hypotheses** for any paradigm (`explore.class_hypotheses` / `case_hypotheses` / …).
- **Leaf review queue**: delta-store ops in the `review` tier (0.5–0.85) with per-op accept/reject.

### 3.5 Decisions log — the audit trail
All decisions already made, filterable by language / paradigm / time:
- **Auto** (Opus verdicts per cell), **Human** (approve/reject/promote), **Leaf** (delta accept/review/defer).
- This is the "task tracker" history — what was decided, when, on what evidence.

---

## 4. The approve model (bake this in — it protects the metric)

Three **separate** write-backs; never conflate them:
- **Approve** ("yes, this is true") → profile status **`confirmed`** + optionally lock the underlying leaf
  deltas (`DeltaStore.decision(accept)`). Means *good enough*.
- **Reject / Defer** → status + recorded verdict.
- **Promote to golden** (the *ceiling*) → a SEPARATE, double-confirmed action that writes a new
  `golden/<lang>_<paradigm>.json`. **Never automatic from Approve** — golden = "best we can author";
  collapsing approved-generated into golden destroys the meaning of completeness/faithfulness.
- **What-if** is a sandbox: writes nothing until explicitly Applied.

---

## 5. Tech & structure
- Streamlit multipage app at `review/paradigm/ui/` (`app.py` + `pages/`). Local, single-user, throwaway.
- Reads JSON directly; calls `run.run`, `sweep.sweep`, `report_review.review_report`, `reviewer_query`,
  `explore`, `DeltaStore`. No new deps beyond `streamlit`.
- `@st.cache_data` on artifact loads; detector scans are already disk-cached. Long ops (live Gemma, full
  sweep) behind buttons with spinners; show cached runs by default so the app is instant.
- Launch: `streamlit run review/paradigm/ui/app.py`.

---

## 6. Build phases
1. **Persistence** — runs store + decisions log in `run.py` (unblocks everything). ~½ day.
2. **Board + Report detail** (read-only) — see all reports, scores, and Opus comments/decisions. ~1 day.
3. **Query / Explore** (read-only). ~½ day.
4. **What-if sandbox** (non-destructive recompute + deltas). ~1 day.
5. **Approve / decisions** write-backs (confirmed + leaf accept; promote-to-golden separate). ~½ day.
6. **Polish** — filters, chip styling, history. ~½ day.

Phases 1–2 deliver the core ask (see reports + Opus thoughts + decisions); 3–4 add queries + what-if; 5
closes the loop (approve). Each phase is usable on its own.

---

## 7. Open questions for you
1. **Approve scope**: status `confirmed` only, or also auto-accept the underlying leaf deltas? *(Recommend: confirm + a checkbox to also accept deltas.)*
2. **Promote-to-golden from the UI**: allow it (double-confirmed) or keep it CLI-only for safety? *(Recommend: allow, double-confirmed.)*
3. **What-if v1 scope**: cell include/exclude + endpoint swap + a few detector sliders enough? *(Recommend: yes; full param matrix later.)*
4. Single-user local only, no auth? *(Assume yes — throwaway.)*
5. **Which reviewer backfills the commentary?** (The centerpiece "what Opus thought.") Today the persisted
   `why` strings are **heuristic templates**, and **`opus` can't run — no `ANTHROPIC_API_KEY`**; the only
   live reviewer is **local-Gemma** (localhost:8080). Options: (a) v1 shows heuristic verdicts, honestly
   labeled "heuristic"; (b) backfill real **Gemma** reviews (slower, but genuine model commentary);
   (c) provide an Anthropic key and backfill **Opus**. *(Recommend: (a) for instant v1, with a "Run Gemma
   review" button per task to upgrade to real commentary; Opus when a key is available.)*
