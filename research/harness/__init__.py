"""Thin, provider-agnostic LLM harness.

One interface (:class:`~harness.base.LLMClient`), two adapters:

- :class:`~harness.openai_compat.OpenAICompatClient` — Ollama / llama.cpp / vLLM
- :class:`~harness.anthropic_client.AnthropicClient` — Claude Opus 4.8

Build a client by name with :func:`~harness.registry.build_client`.
"""

from .base import LLMClient, Message, CompletionResult
from .config import EndpointConfig, DEFAULT_ENDPOINTS
from .registry import build_client

__all__ = [
    "LLMClient",
    "Message",
    "CompletionResult",
    "EndpointConfig",
    "DEFAULT_ENDPOINTS",
    "build_client",
]
