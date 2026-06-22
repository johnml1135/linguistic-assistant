"""Named endpoint configuration.

Edit ``DEFAULT_ENDPOINTS`` (or build :class:`EndpointConfig` directly) to point the
harness at your local servers and models. Model strings below are placeholders — set
them to the exact tags your runtime serves (e.g. an Ollama tag or a HF repo id).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EndpointConfig:
    kind: str  # "openai_compat" | "anthropic"
    model: str
    base_url: str | None = None  # required for openai_compat; ignored for anthropic
    name: str | None = None


DEFAULT_ENDPOINTS: dict[str, EndpointConfig] = {
    # Recommended local backend. Start it with serving/run-ik-llama-server.ps1, which
    # serves a GGUF model at :8080/v1. `model` is ignored by llama-server (any string).
    # THINKING: for a reasoning model (Gemma 4 / Qwen 3.6) run a MAINLINE llama.cpp build with
    # `-Think` (--reasoning on). ik_llama.cpp's jinja path leaves `content` empty for Gemma-4 thinking
    # (chain-of-thought lands only in reasoning_content); mainline splits them correctly. The adapter
    # surfaces the answer as `text` and the chain-of-thought as `reasoning`.
    "ik_llama": EndpointConfig(
        kind="openai_compat",
        model="local",
        base_url="http://localhost:8080/v1",
        name="ik_llama",
    ),
    # vLLM — fastest batched throughput + native JSON-schema enforcement (AWQ/GPTQ).
    # Launch with `vllm serve <repo-id> --port 8000`.
    "vllm": EndpointConfig(
        kind="openai_compat",
        model="Qwen/Qwen3.6-27B",  # set to the repo id vLLM was launched with
        base_url="http://localhost:8000/v1",
        name="vllm",
    ),
    # Optional — Ollama, if you'd rather not build a server. Limited quant control,
    # so less suited to the quantization sweep. Set `model` to your pulled tag.
    "ollama": EndpointConfig(
        kind="openai_compat",
        model="gemma4:27b",
        base_url="http://localhost:11434/v1",
        name="ollama",
    ),
    # Frontier — needs ANTHROPIC_API_KEY.
    "opus": EndpointConfig(
        kind="anthropic",
        model="claude-opus-4-8",
        name="opus-4.8",
    ),
    # Offline pipeline test — deterministic ~25% baseline, no model/network needed.
    "mock": EndpointConfig(
        kind="mock",
        model="mock",
        name="mock",
    ),
}
