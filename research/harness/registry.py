"""Build an :class:`~harness.base.LLMClient` from an :class:`EndpointConfig` or name."""

from __future__ import annotations

from .base import LLMClient
from .config import DEFAULT_ENDPOINTS, EndpointConfig


def build_client(endpoint: str | EndpointConfig, **overrides) -> LLMClient:
    """Resolve a named endpoint (or a config) into a ready client.

    ``overrides`` are passed to the adapter constructor (e.g. ``model=...``,
    ``effort=...``) so a single registered endpoint can be reused with tweaks.
    """
    cfg = DEFAULT_ENDPOINTS[endpoint] if isinstance(endpoint, str) else endpoint

    if cfg.kind == "openai_compat":
        from .openai_compat import OpenAICompatClient

        if not cfg.base_url:
            raise ValueError(f"openai_compat endpoint {cfg.name!r} needs a base_url")
        return OpenAICompatClient(
            base_url=cfg.base_url,
            model=overrides.pop("model", cfg.model),
            name=cfg.name,
            **overrides,
        )

    if cfg.kind == "anthropic":
        from .anthropic_client import AnthropicClient

        return AnthropicClient(
            model=overrides.pop("model", cfg.model),
            name=cfg.name or "opus-4.8",
            **overrides,
        )

    if cfg.kind == "mock":
        from .mock import MockClient

        overrides.pop("model", None)
        return MockClient(name=cfg.name or "mock", **overrides)

    raise ValueError(f"unknown endpoint kind: {cfg.kind!r}")
