## ADDED Requirements

### Requirement: Each switch is presented as a falsifiable, non-linguist claim
The system SHALL present each switch to a speaker as a falsifiable claim: the plain-language presentation
question, the system's current best-guess value + confidence, the corpus evidence (counts + concrete
example forms the speaker recognizes), and the contour options to choose from. The wording SHALL be
jargon-free (a fluent speaker who is not a linguist can answer).

#### Scenario: A switch claim is shown with evidence and options
- **WHEN** the infixation switch is presented for Tagalog
- **THEN** the speaker sees the plain question, "best guess: present (because `tatawag→tinatawag` and 150+
  similar)", and the options present/absent — not the term "infix" alone

### Requirement: The answer space is the contours plus defer
A speaker's response SHALL be one of the switch's contour values or "I don't know" (defer). A confirm or a
correction SHALL be captured as the Phase-0 decision; a defer SHALL leave the switch unconfirmed
(soft prior).

#### Scenario: Confirm, correct, or defer
- **WHEN** the speaker confirms / picks a different contour / defers
- **THEN** the decision (confirmed value | corrected value | unconfirmed) is recorded accordingly

### Requirement: Conflicts with the internet are surfaced in the claim
When the detected value conflicts with the WALS/Grambank seed, the presentation SHALL surface both ("I
think X from the text; reference data says Y") so the human adjudicates, rather than hiding either.

#### Scenario: A conflict is shown, not hidden
- **WHEN** the detector says present but the seed says absent (swh `lakini`)
- **THEN** the claim shows both positions and asks the speaker to decide

### Requirement: Phase-0 switch confirmation precedes per-word work
The switch-confirmation items SHALL be presentable as a distinct Phase-0 review surface (a small set of
~12 claims) that precedes the per-word deferral tickets, so the high-leverage switches are set first and
then constrain the per-word work.

#### Scenario: Switches are a separate, prior review set
- **WHEN** the review queue is built for a new language
- **THEN** the ~12 switch-confirmation items are available as a distinct Phase-0 set, separate from the
  per-word tickets
