"""Adapter for any OpenAI-compatible ``/v1/chat/completions`` endpoint.

Covers the local + self-hosted path: Ollama, llama.cpp's ``llama-server``, and vLLM
all speak this wire format, so the same client drives every local model we benchmark.
"""

from __future__ import annotations

import time
from typing import Any, Sequence

import httpx

from .base import CompletionResult, Message


class OpenAICompatClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        name: str | None = None,
        api_key: str = "not-needed",
        timeout: float = 300.0,
    ) -> None:
        # base_url should include the /v1 suffix, e.g. http://localhost:11434/v1
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = name or model
        self.api_key = api_key
        self._http = httpx.Client(timeout=timeout)

    def complete(
        self,
        messages: Sequence[Message],
        *,
        max_tokens: int = 2048,
        json_schema: dict | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if json_schema is not None:
            # OpenAI-style structured output. vLLM enforces this; Ollama/llama.cpp
            # support varies (Ollama prefers a top-level `format`). Treat as best-effort
            # and validate JSON downstream.
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "schema", "schema": json_schema, "strict": True},
            }
        payload.update(kwargs)

        t0 = time.perf_counter()
        resp = self._http.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        resp.raise_for_status()
        latency = time.perf_counter() - t0

        data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        usage = data.get("usage", {})
        # A reasoning server (llama.cpp --reasoning on / --reasoning-format deepseek, vLLM) separates the
        # chain-of-thought into `reasoning_content`; the final answer is in `content`. We surface the
        # answer as `text` and keep the thoughts in `reasoning`. (NOTE: ik_llama.cpp's jinja path leaves
        # `content` empty for Gemma-4 thinking — use a mainline llama-server build for the thinking path.)
        return CompletionResult(
            text=msg.get("content") or "",
            model=data.get("model", self.model),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_s=latency,
            stop_reason=choice.get("finish_reason"),
            reasoning=msg.get("reasoning_content") or None,
            raw=data,
        )

    def close(self) -> None:
        self._http.close()
