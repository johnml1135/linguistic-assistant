# Tasks — deferral-packages

Each task is tagged **[AUTO]** (deterministic, no model) or **[LLM]** (needs the harness model). Phase A
(groups 1–5) is fully [AUTO] and ships first; Phases B/C are additive and HC-gated.

## 1. Ticket schema + store (Phase A spine) — [AUTO]

- [x] 1.1 [AUTO] Add `research/deferrals/schema.py`: frozen `DeferralTicket` + `Hypothesis` +
  `PresentationOption` + `Resolution` dataclasses with `validate()` and JSONL read/write (mirror
  `parsegym/schema.py`); fields per `specs/deferral-tickets`.
- [x] 1.2 [AUTO] Implement the tracked store `deferrals/<pair>/tickets.jsonl` with load/save and the
  status lifecycle (open → in_review → resolved | wont_fix); round-trip test.
- [x] 1.3 [AUTO] Markdown renderer `render(ticket) -> str` (target, context_md, hypotheses + counterfactual
  diffs, options) derived only from ticket JSON.

## 2. HC counterfactual-parse engine — [AUTO]

- [x] 2.1 [AUTO] `edits.py`: typed grammar-edit ops over `golden.grammar.LangModel` (add LexEntry, add
  MoStemAllomorph, add MoInflAffMsa, add PhonologicalRule, split homograph, re-segment); `apply(edit, model)`
  returns a clone, never mutates the gold.
- [x] 2.2 [AUTO] `related_verses(target)`: deterministic selection by shared root/affix/stem + frequency.
- [x] 2.3 [AUTO] `counterfactual(hypothesis, target)`: clone gold grammar → apply edit → `golden/hc.py`
  run_parse on focus + related verses → `{verse, parse_now, parse_if}` diff; chunked + per-verse timeout;
  time-outs marked `unverified` (per `specs/counterfactual-parsing`).
- [x] 2.4 [AUTO] Smoke test: a known no-parse form + an allomorph edit → focus flips to a parse; gold unchanged.

## 3. Deterministic package builder (Phase A) — [AUTO]

- [x] 3.1 [AUTO] `taxonomy.py`: map deferral `type` → applicable HC mechanisms → candidate `Hypothesis` set
  (no-parse, lexeme-mismatch, unknown-affix, homograph, segmentation).
- [x] 3.2 [AUTO] Presentation-option selector: pick 5–10 archetypes from `parsegym/questions.py` by
  type/hypotheses and slot-fill from the target; tag each with the hypotheses it discriminates.
- [x] 3.3 [AUTO] Compute `impact` (corpus freq × wordforms a fix would newly resolve) and `confidence`
  (source conf + aligner agreement + hypothesis-score margin).
- [x] 3.4 [AUTO] Compute `dependencies` (shared lemma/affix/stem graph over open tickets) + advisory order.
- [x] 3.5 [AUTO] Templated `context_md` fallback (no LLM) so Phase A tickets are complete offline.
- [x] 3.6 [AUTO] `build_ticket(defer_record) -> DeferralTicket` wiring 2.x + 3.x; schema-valid with no endpoint.

## 4. Bug-tracker lifecycle + ledger write-back — [AUTO]

- [x] 4.1 [AUTO] Resolution actions: `accept_option`, `accept_with_words`, `reject_with_reason`; record on ticket.
- [x] 4.2 [AUTO] On accept, emit a confidence-routed op into `deltas/` (map hypothesis edit → delta op;
  decide `accept_with_words` mapping per design Open Question); gold mutated only via that path.
- [x] 4.3 [AUTO] List/sort/filter API by status, domain, impact priority, and dependency order.
- [x] 4.4 [AUTO] CLI `python -m deferrals.build --pair <p>` to backfill tickets from existing `propose.py`
  / sense-pick / affix `defer` records; report counts.

## 5. Phase A verification — [AUTO]

- [x] 5.1 [AUTO] `tests_smoke.py`: schema validate, store round-trip, counterfactual flip, ≥5 options per
  ticket, impact ordering, dependency linking — all offline (no hc.exe required path mocked or skipped).
- [x] 5.2 [AUTO] Backfill the current tgl/swh deferrals → tickets; sanity-check a sample renders correctly.

## 6. Phase B — LLM enrichment (additive, HC-gated) — [LLM]

- [x] 6.1 [LLM] `skills/package_builder.md`: given the ticket + evidence, propose out-of-taxonomy
  hypotheses (typed edits) + select/phrase discriminating options + write `context_md`.
- [x] 6.2 [LLM] Enrichment pass via `harness.build_client`: parse model output → add hypotheses; **run each
  through the 2.3 counterfactual engine and drop/`unverified` any that don't parse** (per `specs/llm-package-enrichment`).
- [x] 6.3 [LLM] Mark model prose non-authoritative; degrade gracefully (skip) when no endpoint; mock-tested.
- [x] 6.4 [AUTO] Eval: on a sample, confirm enrichment never removes deterministic hypotheses and never
  adds an unverified-as-confirmed claim.

## 7. Phase C — workflow escalation (flagged tickets) — [LLM]

- [x] 7.1 [AUTO] Escalation router: trigger only on `impact: high` or dependency-cluster ≥ K.
- [ ] 7.2 [LLM] `Workflow` fan-out: one hypothesis agent per HC mechanism (each builds + HC-tests its edit),
  then a synthesizer agent assembles one schema-valid enriched ticket (ranked options, recomputed deps/impact).
- [ ] 7.3 [AUTO] Verify escalation is additive + HC-verified; low-impact tickets never escalate.

## 8. Stage 1 — auto-accept tier (low-hanging fruit) — [AUTO]+[LLM]

- [x] 8.1 [AUTO] Harden the `propose.py` accept-gate (THOT ∩ LLM-high-conf) into a named tier; tag accepts
  `source: ai-auto`, record both signals, support revert.
- [x] 8.2 [AUTO] Calibrate to ≥99.5% precision against the gold; expose the threshold + the measured number.
- [x] 8.3 [AUTO] Restrict to lexical (gloss/POS) — never auto-accept morphology/phonology; items below the
  bar fall through to the ticket pipeline.

## 9. Stage 2 — candidate selection (next-easiest-thing) — [AUTO]

- [x] 9.1 [AUTO] `select.py`: rank failing/deferred targets by impact (freq × forms affected) + resolvability
  (closeness to a known lemma/affix), from THOT + corpus, no LLM.
- [x] 9.2 [AUTO] Forms→one-lexeme clustering: group surface forms aligning to the same translation word +
  orthographically close into a single candidate.
- [x] 9.3 [AUTO] Use `research/assess/worst_part.py`'s per-construct ablation ranking as a primary input —
  attack the worst part of the grammar next (also the prime suspect for a wrong rule).
- [x] 9.4 [AUTO] Emit ranked candidates feeding stage 3.

## 10. Stage 4 — regression-aware assessment — [AUTO]+[LLM]

- [x] 10.1 [AUTO] Extend the counterfactual engine to a corpus slice: compute **net parse delta = gains −
  regressions** (forms that were parsing and now fail/mis-parse), reported per hypothesis.
- [x] 10.2 [AUTO] Acceptance gate: focus fixed AND net ≥ 0 AND no high-impact regression; deterministic
  score before any model verdict.
- [ ] 10.3 [LLM] LLM verdict presented the HC delta + sample parses; may rank/explain among gate-passing
  hypotheses but CANNOT override the regression rejection.
- [x] 10.4 [AUTO] Wire `research/assess/` as the authoritative "which is better": compute ΔMDL
  (`mdl.py`) + scorecard deltas (`metrics.py`: coverage, spurious ambiguity, generalization,
  over-generation, **productivity/Tolerance**) before-vs-after each hypothesis edit; run the golden
  non-regression gate; rank by ΔMDL. (Depends on the `assess-grammar` change.)
- [x] 10.5 [AUTO] Put the per-hypothesis metric profile (ΔMDL bits, coverage gained, ambiguity added,
  over-generation, productivity vs tolerance, worst-part rank) into the ticket for intelligible presentation.

## 11. Pipeline validation set (ablation) + per-stage scoring — [AUTO]

- [x] 11.1 [AUTO] `ablate.py`: remove a known gold item (LexEntry/allomorph/affix/phon-rule) → re-parse →
  emit scenario `(state, broken forms, ground_truth, type, impact)`; generate hundreds across 4 langs.
- [x] 11.2 [AUTO] Generate **decoy** hypotheses per scenario (fix focus but cause regressions) for stage-4 testing.
- [x] 11.3 [AUTO] Include defer scenarios (correct outcome = defer) by reusing ParseGym `ask_speaker`/`unknown`.
- [x] 11.4 [AUTO] `score_pipeline.py`: per-stage metrics — stage-1 precision (≥99.5%), stage-2 candidate
  recall, stage-3 hypothesis recall (true fix appears?), stage-4 assessment precision + regression-catch —
  plus end-to-end auto-resolution rate; flag any regressed metric.
- [ ] 11.5 [AUTO] Baseline run over spa/ind/tgl/swh; record the starting per-stage numbers to optimize against.

## 12. Noisy-grammar repair + restrictiveness — [AUTO]+[LLM]

- [x] 12.1 [AUTO] Repair hypotheses: narrow/condition, retract, or split an existing rule (typed edits over
  the gold grammar), in addition to additions.
- [x] 12.2 [AUTO] Suspect-rule detection: flag rules implicated in many mis-parses / in other hypotheses'
  regressions as their own tickets.
- [x] 12.3 [AUTO] Restrictiveness via the existing metrics: over-generation + ΔMDL + the Tolerance
  Principle (`assess/`) — the principled form of "subset principle / two narrow rules vs one globbing rule";
  do not reinvent (consume `assess-grammar`).
- [x] 12.4 [AUTO] Narrow-vs-broad presentation: when both viable, surface the coverage↔over-generation trade-off.

## 13. Additional morphological processes — [AUTO]+[LLM]

- [ ] 13.1 [AUTO] Infix discovery in the segmenter + infix hypothesis (HC already supports infix rules);
  validate on tgl -um-/-in-.
- [x] 13.2 [AUTO] Archiphoneme-collapse hypothesis: detect an allomorph family (one function, phonologically-
  conditioned variants) → propose one underlying form + a rule, reusing `cycle/hc_phonology.py`; accept only
  if it round-trips with no regressions.
- [x] 13.3 [AUTO] Tag affix hypotheses inflectional vs derivational (causative/applicative/nominalizer).
- [x] 13.4 [AUTO] Flag-and-stub reduplication (tgl), noun-class concord (swh), and compounding as
  hypothesis types pending their HC representation (follow-on; documented, not yet built).
- [ ] 13.5 [AUTO] Optional: Apertium bidix as a third concurring signal for Stage-1 / candidate evidence.

## 14. Cyclical re-evaluation + state-aware strategy + edge-case presentation — [AUTO]+[LLM]

- [x] 14.1 [AUTO] Re-evaluation loop: on grammar-state change, re-score dependent tickets; promote newly-
  resolvable ones to auto-accept; re-open invalidated ones; iterate to convergence.
- [x] 14.2 [AUTO] State-aware selection/generation: condition stage-2/3 on parsing maturity (cold→lexeme,
  mid→affix/class, near-complete→irregular/phonology/edge).
- [x] 14.3 [AUTO] Edge-case selector: choose the forms the live hypotheses parse DIFFERENTLY (discriminating
  minimal pairs) for the package, not arbitrary examples.
- [ ] 14.4 [LLM] Reparse-question phrasing: "if A, this verse parses as X — correct?" in non-linguist terms.

## 15. Language profile — constrain + configure the solution space — [AUTO]+[LLM]

- [x] 15.1 [AUTO] `profile.py`: frozen `LanguageProfile` schema + `golden_sets/<pair>/profile.json` load/save
  (morphology type, allowed affix processes, allowed phon processes, FsFeatStruc feature space incl.
  gender-vs-noun-class, agreement, orthography, operational config); each feature carries
  `value`/`confidence`/`locked`/`provenance`. Per `specs/language-profile`.
- [x] 15.2 [AUTO] Seed spa/ind/tgl/swh profiles from known typology (WALS/Grambank/Glottolog feature IDs +
  what the gold already evidences); migrate `meta.writing_system` in.
- [x] 15.3 [AUTO] Profile-filter hook in the taxonomy (3.1) + segmenter + assessment: locked-off mechanisms
  pruned, disallowed FsFeatStruc dimensions blocked, uncertain features flagged soft-disfavored for ranking.
- [x] 15.4 [AUTO] Wire the per-language auto-accept bar + pivot + resource flags into stage 1 (8.x) and the
  stage gating (skip a source whose flag is absent).
- [x] 15.5 [AUTO] Feature-probe harness: toggle an uncertain feature → re-run the affected slice → ΔMDL /
  coverage / over-generation via `research/assess/` → recommend a profile update (locked features escalate,
  never auto-flip). Per `specs/language-profile`.
- [x] 15.6 [AUTO] Conflict report: typology-DB feature vs corpus evidence mismatch surfaced (not silently resolved).
- [x] 15.7a [AUTO] Load the pre-written non-linguist explanations from `feature-explanations.md` into each
  feature's `explanation` block (plain meaning + "how to spot it" cue + source links + license); the
  renderer shows them beside the feature/question. Sources: WALS/Grambank (CC-BY-4.0), Wikipedia
  (CC-BY-SA-4.0), SIL Glossary (in-house). Per `specs/language-profile`.
- [ ] 15.7 [LLM] Optional: when no DB entry exists, the harness model proposes a profile feature value +
  rationale from sample data; treated as `provenance: inferred`, unlocked, and probe-verified before trust.

## 16. Docs

- [x] 16.1 [AUTO] `deferrals/README.md`: the 4-stage CYCLICAL pipeline, the AUTO↔LLM boundary, repair +
  restrictiveness, the ablation validation methodology, the linguistic-process coverage, the per-language
  profile (constrain + configure + feature-probing), and how resolutions reach the gold via `deltas/`.
- [x] 16.2 [AUTO] Update memory: the deferral-package + cyclical 4-stage pipeline + ablation validation set
  + the noisy/repair/restrictiveness model + ignored-process list + the language-profile solution-space
  constraint, and where it plugs into propose.py / deltas / harness / parsegym / cycle.hc_phonology / assess.
