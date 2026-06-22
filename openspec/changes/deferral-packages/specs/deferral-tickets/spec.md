## ADDED Requirements

### Requirement: Ticket schema
The system SHALL define a single strict `DeferralTicket` record (JSON, with a rendered markdown view)
carrying: `id`, `pair`, `type` (lexeme_gloss | affix_function | segmentation | phonology_rule | homograph
| pos), `domain` (lexical | morphology | phonology | syntax), `status`, `confidence`, `impact`,
`dependencies`, `target`, `context_md`, `hypotheses`, `presentation_options`, and `resolution`. Every
deferral source (lexical, affix, sense-pick) SHALL emit this same schema.

#### Scenario: A defer record becomes a ticket
- **WHEN** a `defer` record from `propose.py` is converted
- **THEN** a `DeferralTicket` is produced with all required fields populated and validating against the schema

#### Scenario: Markdown view is renderable
- **WHEN** a ticket is rendered
- **THEN** the system produces a human-readable markdown package showing target, context, hypotheses with
  counterfactual parses, and the presentation options — derived only from the ticket JSON

### Requirement: Tracked ticket store with lifecycle
The system SHALL persist tickets in a git-tracked store (`deferrals/<pair>/tickets.jsonl`, one record per
line) and support a status lifecycle: `open` → `in_review` → `resolved` | `wont_fix`. Status transitions
SHALL be recorded on the ticket.

#### Scenario: Tickets persist and reload
- **WHEN** tickets are written and reloaded
- **THEN** every ticket round-trips losslessly and its status is preserved

#### Scenario: Resolve moves status
- **WHEN** a reviewer resolves a ticket
- **THEN** its status becomes `resolved` (or `wont_fix`) and the resolution is stored on the ticket

### Requirement: Tags for triage
The system SHALL tag each ticket with `domain`, `impact` (corpus frequency × wordforms a fix would newly
affect, plus a priority bucket), `confidence`, and `dependencies`, so a tracker can filter and sort.

#### Scenario: Impact prioritises high-value tickets
- **WHEN** tickets are listed by priority
- **THEN** higher-frequency / higher-wordform-impact tickets sort first

### Requirement: Dependency ordering
The system SHALL compute a dependency graph linking tickets that touch the same lemma, affix, or stem, and
SHALL expose an advisory resolution order (unblocking tickets first). Dependencies SHALL NOT prevent a
reviewer from opening any ticket.

#### Scenario: Shared-entity tickets are linked
- **WHEN** two tickets reference the same lemma
- **THEN** each lists the other in `dependencies` and the suggested order surfaces the unblocking one first

### Requirement: Cyclical re-evaluation as the grammar changes
Tickets SHALL be re-evaluated when the grammar state changes (another ticket resolved, a rule added/repaired).
A ticket whose blocking dependency is now resolved SHALL be re-scored; if it becomes confidently resolvable
it MAY be promoted to the Stage-1 auto-accept tier, and a ticket invalidated by a state change SHALL be
re-opened or closed. The loop iterates until no new confident resolutions appear (convergence).

#### Scenario: A dependency resolution promotes a ticket
- **WHEN** ticket B depended on ticket A, and A is resolved (e.g. the lemma is now glossed)
- **THEN** B is re-scored, and if it now meets the auto-accept bar it is resolved without further human input

#### Scenario: A state change re-opens an invalidated ticket
- **WHEN** a rule repair invalidates a previously-resolved ticket's assumption
- **THEN** that ticket is re-opened for re-assessment

### Requirement: Structured resolution writes back to the ledger
A ticket SHALL accept exactly one resolution action: `accept_option` (choose a hypothesis),
`accept_with_words` (choose + supply extra forms), or `reject_with_reason`. A non-reject resolution SHALL
emit a confidence-routed op into the `deltas/` ledger so the answer flows to the gold through the existing
applier; the gold SHALL NOT be mutated except through that path.

#### Scenario: Accepting a hypothesis emits a delta
- **WHEN** a reviewer accepts hypothesis A
- **THEN** a corresponding `deltas/` op is written and the ticket records the chosen hypothesis

#### Scenario: Rejection captures the reason
- **WHEN** a reviewer rejects all hypotheses with a reason
- **THEN** the ticket stores the reason, no `deltas/` op is emitted, and status becomes `wont_fix`
