## Why

A language has ~12 high-level **master switches** (typological parameters) that, once set, constrain
everything downstream: is it prefixing or suffixing? does it infix? reduplicate? have noun classes? mark
tense on the verb? Today these are implicit, scattered, or pulled only from the internet (WALS/Grambank) —
and for the thin languages (tgl/swh) the internet is too sparse to set them.

But we can **detect most of them from the corpus itself**, using pieces we already have (`profile_detect.py`
proved this: it recovered Tagalog infixation `-in-`×154 and Swahili head-marking from the text). So the
right shape is: **detect each switch from the corpus, present it to a speaker as a falsifiable,
evidence-backed claim ("I think it's X because of this — am I right?"), cross-check the internet as a
second opinion, record the confirmed decision in the language profile, and have every successive step read
and be constrained by it.** Confirming ~12 switches up front is the cheapest, highest-leverage human
interaction in the system — it turns the frontier from "fetch the morphology" into a short Phase-0 screen.

## What Changes

- A **catalog of the 12 master switches**, each with: a non-linguist **presentation** (the question/claim),
  the **corpus evidence** to assemble so the speaker can judge it, its **contours** (allowed values), and
  the **downstream constraint** it sets. (Defined in `specs/switch-catalog`.)
- **Corpus detection** for each switch (extending `profile_detect.py`): produces `value + confidence +
  evidence`, gated by a **productivity test** (Tolerance Principle, `assess/`) so coincidental-substring
  false positives (swh `lakini`, spa `dejando`) drop out.
- An **internet cross-check**: compare each detected value to the WALS/Grambank seed; **agreement** boosts
  confidence, **conflict** is surfaced to the human — the internet is a second opinion, not the source.
- **Falsifiable presentation**: each switch is shown as a claim + its evidence + the contour options, in
  plain language a non-linguist speaker can confirm/correct (a Phase-0 "switch-confirmation" review).
- **Recorded in configuration**: the confirmed decision is written to the per-language profile
  (`golden_sets/<pair>/profile.json`) with `value / confidence / provenance (detected|internet|linguist) /
  evidence / locked`. **Every successive step SHALL read the profile and be constrained by it** — a locked
  switch hard-prunes disallowed hypotheses (no Spanish infix), an uncertain one is a soft prior.

## Capabilities

### New Capabilities
- `switch-catalog`: the 12 master switches as a fixed, versioned catalog — each defining its presentation
  text, contours (allowed values), the corpus evidence to assemble, and the downstream constraint it sets.
- `switch-detection`: detect each switch from the corpus (value + confidence + evidence), productivity-
  gated, and cross-check the WALS/Grambank seed (agree → boost, conflict → surface).
- `switch-configuration`: record confirmed switches in the per-language profile with provenance/evidence/
  locked, and **constrain all successive analysis** by them (the load-bearing requirement).
- `switch-presentation`: present each switch as a falsifiable, evidence-backed, non-linguist claim and
  capture the speaker's confirm/correct as the Phase-0 decision (a switch-confirmation review item).

## Impact

- **New/extended code** under `research/deferrals/`: `profile_detect.py` (add the productivity gate + the
  remaining detectors), `profile.py` (the switch fields + `provenance="detected"` + the constrain hooks),
  `feature_explanations.py` (the non-linguist presentation text). A `switches.py` catalog module pins the
  12 definitions.
- **Reuses (no breaking changes)**: `cycle/out/<pair>_model.json` (induced affixes), `golden/reference/
  phonology_induce.py` (harmony/assimilation), `align/morph_align_hc.py` outputs (TAM/agreement/articles),
  `golden/reference/orthography.py` (tone/script), `assess/` (the Tolerance productivity gate), and the
  `deferrals/` ticket + review path (the Phase-0 confirmation surface).
- **Constrains downstream**: the taxonomy / induction / gold-raise already read the profile's allowed
  affix-kinds + feature space; this change makes the *source* of those settings the detected+confirmed
  switches, so a confirmed switch genuinely enables/prunes future analysis.
- **No change** to the frozen gold except via the profile (config), which is reviewed + reversible.
