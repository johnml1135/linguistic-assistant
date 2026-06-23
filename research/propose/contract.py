"""The cross-agent contract for the eval/proposal loop.

These shapes are the *seam* between this harness and the sibling golden-set work
(`research/golden/`). We depend on structural ``Protocol``s (``Instance``, ``Scorer``) rather than
importing the sibling's concrete classes, so the two trees can evolve independently. Keep this module
dependency-free (stdlib only) — it is imported by both sides.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class IGTRecord:
    """One interlinear record the agent may see (raw input, req. 2 of the golden design)."""

    id: str
    text: str  # orthography (\t)
    translation: str = ""  # free translation (\l)
    segmentation: str | None = None  # \m — only present on the "easy" track
    gloss: str | None = None  # \g — the oracle; normally withheld from the agent
    pos: str | None = None  # \p — present for some languages


@dataclass
class Case:
    """What ``propose()`` consumes — identical for golden (answer-keyed) and real cases.

    ``lexicon_lift`` / ``grammar_hcgr`` are the *incomplete* artifacts (after ablation, for golden;
    the current FLEx export, for real). They are kept as text blobs: the propose core treats them as
    evidence to read, never as a database to write (project scope = emit change-sets, not DB writes).
    """

    glottocode: str
    igt: list[IGTRecord]
    lexicon_lift: str = ""  # incomplete LIFT XML
    grammar_hcgr: str = ""  # incomplete Hermit Crab grammar XML
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeSet:
    """A proposal: a list of validated change-set operations (plain dicts; schema in change_set.py)."""

    ops: list[dict[str, Any]]

    def signatures(self) -> set[tuple[str, str]]:
        """Canonical (op_type, key) signatures, for set-overlap scoring/diffing."""
        from .change_set import op_signature

        return {op_signature(op) for op in self.ops}


@dataclass
class ValidationFailure:
    """Returned instead of a ChangeSet when model output can't be validated. Never applied."""

    reason: str
    raw_text: str = ""


# A proposal attempt is one or the other; callers check isinstance.
ProposalResult = ChangeSet | ValidationFailure


@dataclass
class ScoreResult:
    """The Scorer's verdict. ``reward`` ∈ [0,1] (golden design: HC re-parse gated on non-regression)."""

    reward: float
    parsed_ok: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Instance(Protocol):
    """A golden instance. The hidden answer key lives on the sibling's concrete type, not here."""

    id: str
    glottocode: str
    tier: str

    @property
    def case(self) -> Case: ...


@runtime_checkable
class Scorer(Protocol):
    """The deterministic ``(instance, proposal) -> reward`` function owned by the golden-set work."""

    name: str

    def score(self, instance: Instance, change_set: ChangeSet) -> ScoreResult: ...
