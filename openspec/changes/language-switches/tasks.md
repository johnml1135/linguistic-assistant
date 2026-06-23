# Tasks — language-switches

Tagged **[AUTO]** (deterministic) or **[GATED]** (needs cycle output / `hc` / cached morpheme alignment).
Builds on the existing `deferrals/profile_detect.py`, `profile.py`, `feature_explanations.py`, and the
`assess/` Tolerance metric.

## 1. The catalog — [AUTO]

- [ ] 1.1 [AUTO] `deferrals/switches.py`: the fixed, versioned 12-switch catalog — each entry with
  `id`, `presentation` (non-linguist text), `contours` (allowed values), `evidence_spec` (what to assemble
  + source pieces), `constraint` (downstream enable/prune). Per `specs/switch-catalog`.
- [ ] 1.2 [AUTO] Move the non-linguist presentation text into `feature_explanations.py` (reuse the
  open-licensed explanations) and reference it from the catalog.
- [ ] 1.3 [AUTO] Catalog test: exactly the 12 ids; each has presentation + contours + evidence + constraint.

## 2. Detection + productivity gate — [AUTO]+[GATED]

- [ ] 2.1 [AUTO] Add the **Tolerance-Principle productivity gate** (`assess/`) to `detect_infixation` and
  `detect_reduplication`: report `present` only above a distinct-stem threshold (kills swh `lakini`, spa
  `dejando`). Per `specs/switch-detection`.
- [ ] 2.2 [GATED] Add the missing detectors: `gender_or_noun_class` (systematic sg/pl prefix-pairs +
  concord covariance → class count) and `case` (role-correlated noun-suffix covariance, or attested absence).
- [ ] 2.3 [AUTO] Each detector returns `value + confidence + evidence`; missing evidence → `unknown` (conf 0).
- [ ] 2.4 [AUTO] Internet cross-check (already in `profile_detect`): agree → boost, conflict → flag; cover
  all 12. Calibrate the productivity threshold on spa/ind/tgl/swh (known answers).
- [ ] 2.5 [AUTO] Detection determinism test + a per-language regression of the detected switch set.

## 3. Configuration: record + constrain — [AUTO]

- [ ] 3.1 [AUTO] `profile.py`: switch fields with `value / confidence / provenance / evidence / locked`;
  `write_switches(profile, detected, confirmations)` records them; round-trip test.
- [ ] 3.2 [AUTO] Map each switch → its downstream constraint (extend `allowed_affix_kinds` /
  `allowed_edit_kinds` / the FsFeatStruc dimension) so a locked switch hard-prunes and an uncertain one is
  a soft prior. Per `specs/switch-configuration`.
- [ ] 3.3 [AUTO] **Binding test**: assert the taxonomy/segmenter read the profile switches (e.g. infixation
  locked-absent ⇒ no infix hypothesis; noun-class ⇒ no gender feature). The load-bearing guarantee.
- [ ] 3.4 [AUTO] Probe hook: a locked switch is never auto-flipped; the ΔMDL probe only *recommends*.

## 4. Presentation: the Phase-0 confirmation — [AUTO]

- [ ] 4.1 [AUTO] Render each switch as a claim: presentation + best-guess + confidence + evidence
  (counts + example forms) + contour options + the internet conflict (if any). Per `specs/switch-presentation`.
- [ ] 4.2 [AUTO] A switch-confirmation review item (a distinct Phase-0 set, separate from per-word tickets);
  capture confirm / correct / defer → `write_switches`.
- [ ] 4.3 [AUTO] Surface the Phase-0 switch set in `deferrals/webui.py` (or a queue view) ahead of per-word tickets.

## 5. Run + record the four languages — [GATED]

- [ ] 5.1 [GATED] Run detection on spa/ind/tgl/swh; produce the 12-switch claim set per language with evidence.
- [ ] 5.2 [GATED] Record the (human-confirmed where available) switch sets into each profile as the
  languages' configuration; show that it constrains a subsequent taxonomy run.

## 6. Docs

- [ ] 6.1 [AUTO] `deferrals/README.md` + `docs/w6-coverage-experiment.md`: the 12-switch catalog, the
  detect → present → cross-check → record → constrain flow, and Phase-0's place in the workflow.
- [ ] 6.2 [AUTO] Update memory: the master-switch catalog + that confirmed switches are recorded config that
  constrains all successive steps (where it plugs into profile / profile_detect / taxonomy / the review UI).
