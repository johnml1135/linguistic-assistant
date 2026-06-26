"""Adapter for Claude Opus 4.8 via the official Anthropic SDK.

This is the BYOK/frontier path *and* the data-generation / LLM-as-judge engine. For
large offline generation jobs, prefer the Batch API (50% discount) with prompt caching
of the shared grammar/typology context — see ``docs/plans/data-gen-plan.md``; this client covers
the synchronous single-request path used for smoke tests and interactive checks.
"""

from __future__ import annotations

import time
from typing import Any, Sequence

import anthropic

from .base import CompletionResult, Message, split_system

# Per the project's Claude reference: always use this exact id unless told otherwise.
DEFAULT_MODEL = "claude-opus-4-8"


class AnthropicClient:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        name: str = "opus-4.8",
        api_key: str | None = None,
        effort: str = "high",
        thinking: bool = True,
    ) -> None:
        # Falls back to ANTHROPIC_API_KEY / profile resolution when api_key is None.
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model
        self.name = name
        self.effort = effort
        self.thinking = thinking

    def complete(
        self,
        messages: Sequence[Message],
        *,
        max_tokens: int = 1024,
        json_schema: dict | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        system, conv = split_system(messages)
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in conv],
        }
        if system:
            params["system"] = system

        # Structured output: SDK 0.71 has no native json_schema/output_config. Use FORCED TOOL USE — a
        # single tool whose input_schema is the requested schema, with tool_choice pinned to it. Forced
        # tool_choice is incompatible with extended thinking, so thinking is disabled for schema calls.
        if json_schema is not None:
            params["tools"] = [{"name": "emit", "description": "Return the structured result.",
                                "input_schema": json_schema}]
            params["tool_choice"] = {"type": "tool", "name": "emit"}
        elif self.thinking:
            params["thinking"] = {"type": "adaptive"}  # adaptive is the supported mode on Opus 4.8

        params.update(kwargs)

        t0 = time.perf_counter()
        resp = self._client.messages.create(**params)
        latency = time.perf_counter() - t0

        if json_schema is not None:
            tool_inputs = [b.input for b in resp.content if getattr(b, "type", "") == "tool_use"]
            import json as _json
            text = _json.dumps(tool_inputs[0], ensure_ascii=False) if tool_inputs else \
                "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
        else:
            text = "".join(b.text for b in resp.content if b.type == "text")
        return CompletionResult(
            text=text,
            model=resp.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            latency_s=latency,
            stop_reason=resp.stop_reason,
            raw=resp,
        )
