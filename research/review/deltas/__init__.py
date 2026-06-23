"""Accumulating, confidence-routed delta store — the controllable backend for proposed LibLCM edits.

The cycle/LLM emit change-set ops; this package merges them (idempotent by signature) across many runs,
routes each by confidence (accept / review / defer), and persists a committable JSONL that appliers
(MiniLcm/Harmony, FLExTools/flexlibs) consume. See store.py, emit.py, build_store.py.
"""

from .store import DeltaStore, RouteResult

__all__ = ["DeltaStore", "RouteResult"]
