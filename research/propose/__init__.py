"""Proposal harness: turn a Case into a validated lexicon/morphology change-set.

The shared core for both golden evaluation and real (unknown-answer) proposing.
"""

from __future__ import annotations

from .change_set import OP_TYPES, op_signature, validate_change_set
from .context import DEFAULT_SKILL, assemble_context, compile_primer
from .contract import (
    Case,
    ChangeSet,
    IGTRecord,
    Instance,
    ProposalResult,
    ScoreResult,
    Scorer,
    ValidationFailure,
)
from .grammar import change_set_gbnf, change_set_json_schema, schema_hint
from .propose import ProposeConfig, propose

__all__ = [
    "Case",
    "IGTRecord",
    "ChangeSet",
    "ValidationFailure",
    "ProposalResult",
    "ScoreResult",
    "Instance",
    "Scorer",
    "OP_TYPES",
    "op_signature",
    "validate_change_set",
    "compile_primer",
    "assemble_context",
    "DEFAULT_SKILL",
    "change_set_gbnf",
    "change_set_json_schema",
    "schema_hint",
    "propose",
    "ProposeConfig",
]
