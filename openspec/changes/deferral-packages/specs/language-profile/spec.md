## ADDED Requirements

### Requirement: First-class per-language profile constrains and configures the solution space
The system SHALL maintain a per-language profile (`golden_sets/<pair>/profile.json`) that both **prunes**
the hypothesis/solution space and **configures** operational thresholds. The profile SHALL be a tracked,
human-readable, first-class artifact loaded by candidate selection, hypothesis generation, assessment, and
the auto-accept tier. It SHALL declare at least: morphological typology and **allowed affixation processes**
(prefix / suffix / infix / circumfix / reduplication / compounding); allowed **phonological processes**
(vowel harmony, nasal/place assimilation, tone, the relevant segment/place features); the **morphosyntactic
feature space** (which FsFeatStruc dimensions exist and their value sets — including **gender vs noun-class**,
case, definiteness, TAM, person/number) plus agreement/concord targets and basic word order; the
**orthography** (script, digraphs, diacritics, segment inventory, number format); and **operational config**
(per-language auto-accept precision bar, pivot language, resource flags, Tolerance/confidence parameters).

#### Scenario: Profile loaded before the solution space is searched
- **WHEN** any stage that proposes or ranks hypotheses runs for a pair
- **THEN** it reads that pair's profile and applies its constraints and config

### Requirement: Locked features hard-prune disallowed hypotheses
A profile feature marked `locked` SHALL be a HARD constraint: hypotheses of a disallowed type SHALL NOT be
enumerated by the taxonomy, the segmenter, or the LLM enrichment layer, and disallowed FsFeatStruc
dimensions SHALL NOT be assigned. This keeps the search tractable and prevents spurious rules.

#### Scenario: No Spanish infix proposed
- **WHEN** building hypotheses for a Spanish no-parse form and the profile locks infixation = false
- **THEN** no infix hypothesis is enumerated (only the allowed prefix/suffix/stem-alternation mechanisms)

#### Scenario: Noun-class not gender for Swahili
- **WHEN** assigning agreement features for Swahili and the profile declares noun-class (not gender M/F)
- **THEN** hypotheses use the declared noun-class dimension and never invent a gender feature

### Requirement: Uncertain features are soft priors, not prohibitions
A feature that is not `locked` (low/medium confidence) SHALL act as a SOFT prior: hypotheses against it are
deprioritized in ranking but still allowed and eligible for probing. The profile SHALL record per-feature
`confidence`, `locked`, and `provenance` (WALS / Grambank / Glottolog / linguist / inferred-from-corpus).

#### Scenario: Soft-disfavored hypothesis still considered
- **WHEN** reduplication is present-but-uncertain in the profile
- **THEN** reduplication hypotheses are ranked lower but not pruned, and remain probe-eligible

### Requirement: Per-language operational configuration
Stages SHALL read the auto-accept precision bar (e.g. 99.5% vs 99.9%), the pivot language, and the resource
flags (has UniMorph / Wiktionary / audio) from the profile per language; they SHALL honor the per-language
bar and SHALL skip any source/stage whose required resource flag is absent.

#### Scenario: Stricter language uses a higher bar
- **WHEN** a pair's profile sets the auto-accept bar to 99.9%
- **THEN** the auto-accept tier calibrates to and reports against 99.9% for that pair, not the default 99.5%

#### Scenario: Missing resource skips its stage
- **WHEN** the profile marks UniMorph as unavailable for a pair
- **THEN** the UniMorph-dependent generation path is skipped rather than failing

### Requirement: Features are testable hypotheses ("what if this feature were different")
The system SHALL be able to probe an uncertain profile feature by toggling it, re-running the affected
pipeline slice, and comparing grammars via the `research/assess/` metrics (**ΔMDL**, coverage,
over-generation) over the gold/corpus. If a toggle materially improves the grammar with no regression, the
system SHALL recommend a profile update with the supporting evidence. `locked` features SHALL NOT be
auto-flipped — a recommendation for a locked feature is surfaced to a linguist, not applied.

#### Scenario: Enabling reduplication improves the grammar
- **WHEN** reduplication is toggled on for Tagalog and the reparse lowers MDL and raises coverage with no regression
- **THEN** the system recommends setting reduplication = present in the profile, with the metric deltas as evidence

#### Scenario: Locked feature change is escalated, not applied
- **WHEN** a probe suggests flipping a `locked` feature
- **THEN** the recommendation is surfaced for linguist review and the profile is not changed automatically

### Requirement: Every feature carries a pre-written non-linguist explanation
Each profile feature SHALL carry a plain-language `explanation` block written for a fluent speaker who is not
a trained linguist: a jargon-free meaning, a "how to spot it in your own language" cue, and one or more
source links with their license. The deferral renderer and any profile UI SHALL show this explanation next
to the feature/question so a reviewer understands the term before answering. The explanations SHALL be
seeded from the curated `feature-explanations.md` glossary (project-original prose grounded in open-licensed
sources: WALS CC-BY-4.0, Grambank CC-BY-4.0, Wikipedia CC-BY-SA-4.0, and the SIL *Glossary of Linguistic
Terms* as an in-house SIL resource), and source attributions/licenses SHALL be preserved.

#### Scenario: A feature question shows its explanation
- **WHEN** a profile feature (e.g. reduplication) is presented for review or probing
- **THEN** the plain-language meaning, a "how to spot it" cue, and at least one open-licensed source link are shown

#### Scenario: Attribution and license are preserved
- **WHEN** an explanation quotes or adapts an open-licensed source
- **THEN** the source link and its license (e.g. WALS CC-BY-4.0) travel with the explanation

### Requirement: Profiles are internet-seeded and corpus-reconciled
The profile SHALL be seedable from typological databases (WALS / Grambank / Glottolog) where available, with
provenance recorded, and SHALL be reconciled against corpus evidence. A conflict between a database feature
and corpus evidence SHALL be surfaced (the same "validate against internet data" discipline as the lexicon),
not silently resolved.

#### Scenario: Database/corpus conflict surfaced
- **WHEN** a typology database asserts a feature absent that the corpus appears to evidence
- **THEN** the conflict is reported for review rather than one source silently overriding the other
