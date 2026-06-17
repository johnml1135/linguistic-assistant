"""A clearly-labeled STUB scorer so the loop runs before the sibling's real HC scorer exists.

This is NOT the golden scorer. The real one (research/golden/, per the golden-set design) applies the
change-set, runs Hermit Crab, and rewards re-parse coverage gated on non-regression. The stub only
checks op-signature overlap against a fixture answer key, for pipeline testing.
"""

from __future__ import annotations

from proposal.contract import ChangeSet, Instance, ScoreResult


class StubScorer:
    name = "stub(NOT-the-golden-HC-scorer)"

    def score(self, instance: Instance, change_set: ChangeSet) -> ScoreResult:
        expected: set[tuple[str, str]] = set(getattr(instance, "answer_key", set()))
        got = change_set.signatures()
        if expected:
            matched = expected & got
            reward = len(matched) / len(expected)
        else:
            matched = set()
            reward = 1.0 if got else 0.0
        return ScoreResult(
            reward=reward,
            parsed_ok=True,
            diagnostics={
                "scorer": self.name,
                "matched": sorted(f"{a}:{b}" for a, b in matched),
                "expected": sorted(f"{a}:{b}" for a, b in expected),
                "proposed": sorted(f"{a}:{b}" for a, b in got),
            },
        )
