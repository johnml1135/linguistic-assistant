# read-the-gate

> Interpret the regression gate — golden-set round-trip plus integrity checks — and decide **commit /
> revise / revert**; a change earns its place only when failures drop *and* no regressions appear.

**Judgment type:** verify  ·  **Grounded in:** the engine+oracle principle (golden `word→gloss` set);
Maxwell (1994) generate-and-test; AQuA-style assessment (precision/recall vs an annotated set) for
parallel-QA  ·  **Used by:** all
change workflows ([[../workflows/morphological-parser-setup]], [[../workflows/interlinearization]],
[[../workflows/parallel-translation-qa]]) and [[../meta-workflows/test-a-grammar-theory]]

## The judgment

No proposal is "done" because it *looks right*. It is done when the oracle — the golden `word→gloss`
set and the integrity checks — confirms it without collateral damage. This skill reads that evidence
and returns one of three verdicts: **commit**, **revise**, or **revert**. The central discipline is
separating two numbers that a naive "tests pass" glance conflates: **failures resolved** (the wins the
change was meant to deliver) and **regressions introduced** (forms that parsed correctly before and
now don't). A change that fixes N but breaks M is not a pass — it is a judgment call, and the default
is *revise*, not *force it through*.

Because Hermit Crab applies ordered rules in **reverse** to analyze (Maxwell 1994), a change must pass
**both directions**: generate the expected surface forms *and* parse them back to the right analysis.
A rule that generates correctly can still mis-order and parse silently wrong (see
[[../primitives/stratum]], [[../primitives/phonological-rule]]). "It loaded" is not "it's correct":
[[../workflows/data-integrity-check]] catches **dangling references** and **silently-skipped rule
ids** — rules the engine quietly ignored rather than applied.

## Heuristic / procedure

```
After running the change against the gate:
1. Integrity first — dangling refs / silently-skipped rule ids?
        → ANY present → REVISE (the change isn't really wired in; "loaded" ≠ "applied")
2. Round-trip — does BOTH parse AND generate pass on the golden set?
        → generate-only pass → REVISE (likely rule-ordering; reverse-analysis fails)
3. Compare counts:
   ├─ failures DOWN, regressions ZERO        → COMMIT
   ├─ failures DOWN, regressions > 0         → REVISE (fix the M, or add a restriction); never force
   └─ failures NOT down (no wins delivered), esp. with new breakage → REVERT
4. Parallel-QA flags: score precision/recall vs the annotated set (AQuA-style) before accepting.
```

Coverage-up-with-regressions is a **fail**, not a tradeoff to negotiate.

## Inputs → outputs

- **In:** a proposed change (rule, allomorph, sense, QA flag) and the gate results — golden-set
  parse/generate outcomes, integrity report, and (for QA) precision/recall against the annotated set.
- **Out:** a verdict — **commit** (with the resolved-vs-regressed counts), **revise** (with the
  specific regressions or integrity faults to fix), or **revert** (with why) — recorded on the change.

## Interaction with other skills & the gate

This skill *is* the gate every other change skill must clear. It bounds
[[generalize-not-enumerate]] (over-generalization shows up as regressions here), accepts or rejects
[[propose-from-evidence]] and [[divide-senses]] outputs, and converts a "guess" from
[[guess-ask-or-defer]] into a committed change only on a clean pass.

## Failure modes / guardrails

- **Accepting on "looks right"** — the prohibited move; require gate evidence, never intuition.
- **Coverage-up, regressions ignored** — a net-positive count still fails if it silently breaks
  working forms.
- **Generate-only verification** — skipping the reverse parse misses rule-ordering bugs that parse
  silently wrong (Maxwell 1994).
- **Trusting "it loaded"** — without [[../workflows/data-integrity-check]], dangling or silently-skipped
  rule ids mean the change isn't doing what it claims. *(Exact integrity-check output fields are
  implementation-dependent — unverified.)*

## Training basis

The engine+oracle / generate-and-test principle: an analysis is validated by round-tripping it
through the engine against held-out gold data (Maxwell 1994; HC reference, Maxwell 2003). For
parallel-translation flags, precision/recall against an annotated set follows AQuA's assessment frame
(accuracy / clarity / naturalness). See [../References.md](../References.md) §1.
