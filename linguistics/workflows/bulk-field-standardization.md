# Bulk field standardization

> Apply one normalization across many entries at once — assign a field, fill a default, convert a
> custom field into a structured one — as a previewed, reviewed batch of change-set ops.

**Primary tool(s):** FLEx Bulk Edit; FlexTools *Approve Spelling of Numbers*, *Convert Custom Plurals
to Variants*, Chinese utilities  ·  **Mode:** change  ·  **Stage in our loop:** propose + review +
gate  ·  **Parallel-aware:** no

## Goal & when it runs

The "change this from here to there" workflow at scale: a single rule applied across a class of
entries (set [[part-of-speech]] for a group, fill a missing default, normalize a writing-system
field, restructure a custom field into [[variant-form]]s, mark a spelling status). It usually runs
*after* an [[lexicon-consistency-audit]] or [[data-integrity-check]] identifies a systematic gap.

## The human process (in FLEx today)

- FLEx **Bulk Edit** sets a field across filtered entries.
- FlexTools change modules do targeted batch transforms: *Approve Spelling of Numbers* (mark numeric
  wordforms "Correct"), *Convert Custom Plurals to Variants* (custom field → real variants), the
  Chinese Pinyin/tone/sort generators. Each declares `FTM_ModifiesDB` and follows **preview-then-apply**
  — report what *would* change, then change it only when modification is enabled.

## How the assistant supports it

- Express the edit as a **scope predicate + transform** ("for entries matching P, set F = V"),
  propose it, and show the **preview**: the full list of `lexical/*` (or `morphophonology/*`) ops it
  would emit, each with rationale/confidence/impact/provenance.
- **Our change-set is the dry-run.** It is the externalized analogue of FlexTools' `FTM_ModifiesDB`
  preview and FlexToolsMCP's `write_enabled=False` → `True` two-phase guard: nothing is applied until
  a human approves the batch.
- Decide *apply confidently / show each for confirmation / ask a speaker* per the edit's risk.

## Inputs

The lexicon, a scope predicate (filter), the target field/value, and the audit/integrity findings
that motivated the batch.

## Primitives involved

[[lexical-entry]], [[sense]], [[part-of-speech]], [[variant-form]], [[homograph-number]];
writing-system–scoped fields ([[writing-system]]).

## Oracle / gold / metrics

Each op is individually reviewable; correctness is checked against the golden set / parallel-QA where
the field affects parsing or meaning. Report scope size (how many entries touched) up front.

## Outputs

A reviewed batch of `lexical/*` (occasionally `morphophonology/*`) change-set ops.

## Pitfalls

- **Bulk edits are high-blast-radius** — a wrong predicate corrupts hundreds of entries. Always
  preview the full affected set; never apply blind. Downstream, flexlibs runs batch writes in a
  **non-undoable** unit of work (no per-op rollback), so a half-applied bulk edit can corrupt data —
  another reason the reviewed change-set (atomic, inspectable) is safer than driving the DB directly.
- **Over-broad predicates** silently catch exceptions; favor narrow scopes + explicit exclusions.

## References

FLEx Bulk Edit docs; FlexTools change modules & `FTM_ModifiesDB` preview pattern; FlexToolsMCP
dry-run/write guard; flexlibs transaction notes. See [../References.md](../References.md).
