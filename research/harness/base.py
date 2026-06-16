"""Core types shared by every adapter.

The whole point of the harness is that benchmark and data-gen code depends only on
this interface — never on a specific provider SDK. Local models and Opus 4.8 are
swapped by config, not by code changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence, runtime_checkable


@dataclass
class Message:
    """A single chat turn. ``role`` is ``"system"``, ``"user"``, or ``"assistant"``."""

    role: str
    content: str


@dataclass
class CompletionResult:
    """Normalized result. ``raw`` keeps the provider-native object for debugging."""

    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_s: float | None = None
    stop_reason: str | None = None
    raw: Any = None


@runtime_checkable
class LLMClient(Protocol):
    """The one interface every benchmark/data-gen caller programs against."""

    name: str

    def complete(
        self,
        messages: Sequence[Message],
        *,
        max_tokens: int = 1024,
        json_schema: dict | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        """Run one completion.

        ``json_schema`` (when given) requests structured JSON output constrained to that
        schema. Support varies by endpoint — Opus 4.8 and vLLM enforce it; some local
        servers only best-effort. Adapter-specific knobs (``temperature``, ``effort``,
        …) ride through ``**kwargs``.
        """
        ...


def split_system(messages: Sequence[Message]) -> tuple[str | None, list[Message]]:
    """Pull ``system`` turns out of a message list (Anthropic keeps system separate)."""
    system = "\n\n".join(m.content for m in messages if m.role == "system") or None
    rest = [m for m in messages if m.role != "system"]
    return system, rest
