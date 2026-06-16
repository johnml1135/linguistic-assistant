"""A deterministic offline client for end-to-end pipeline tests (no model needed).

Returns an A-D letter chosen by a seeded hash of the prompt, so a full benchmark run
produces a stable ~25% (random-baseline) accuracy. Use it to validate the dataset
loader, prompt builder, scorer, and aggregation without a GPU or network.
"""

from __future__ import annotations

import hashlib
from typing import Any, Sequence

from .base import CompletionResult, Message


class MockClient:
    def __init__(self, *, name: str = "mock", seed: int = 0) -> None:
        self.name = name
        self.seed = seed

    def complete(
        self,
        messages: Sequence[Message],
        *,
        max_tokens: int = 1024,
        json_schema: dict | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        prompt = "".join(m.content for m in messages)
        digest = hashlib.sha256(f"{self.seed}:{prompt}".encode("utf-8")).hexdigest()
        letter = "ABCD"[int(digest[:8], 16) % 4]
        return CompletionResult(
            text=letter,
            model="mock",
            input_tokens=max(1, len(prompt) // 4),
            output_tokens=1,
            latency_s=0.0,
            stop_reason="stop",
        )
