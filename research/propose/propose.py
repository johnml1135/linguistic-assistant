"""The propose core: ``Case -> ChangeSet | ValidationFailure``.

Backend-, golden-, and answer-key-agnostic. This is the exact code reused for real (no-answer-key)
proposing — golden eval just wraps it with a scorer. Direct local control (GBNF grammar, cache_prompt,
seed) rides the existing ``openai_compat`` kwargs seam; the Anthropic/BYOK path uses ``json_schema``.
"""

from __future__ import annotations

from dataclasses import dataclass

from propose.harness.base import LLMClient

from .change_set import validate_change_set
from .context import assemble_context
from .contract import Case, ChangeSet, ValidationFailure
from .grammar import change_set_gbnf, change_set_json_schema


@dataclass
class ProposeConfig:
    backend_kind: str = "openai_compat"  # "openai_compat" | "anthropic" | "mock"
    seed: int = 13
    temperature: float = 0.0  # greedy by default → reproducible
    max_tokens: int = 2048
    use_grammar: bool = True  # GBNF constraint on the local path
    cache_prompt: bool = True  # reuse the primer KV prefix across cases (ik_llama)
    skill: str | None = None


def propose(case: Case, client: LLMClient, cfg: ProposeConfig | None = None) -> ChangeSet | ValidationFailure:
    """Assemble context, call the model with constrained output, validate the result."""
    cfg = cfg or ProposeConfig()
    messages = assemble_context(case, skill=cfg.skill)

    kwargs: dict = {"max_tokens": cfg.max_tokens}
    if cfg.backend_kind == "openai_compat":
        # Direct llama.cpp/ik_llama control via the kwargs passthrough.
        kwargs["temperature"] = cfg.temperature
        kwargs["seed"] = cfg.seed
        kwargs["cache_prompt"] = cfg.cache_prompt
        if cfg.use_grammar:
            kwargs["grammar"] = change_set_gbnf()
        else:
            kwargs["json_schema"] = change_set_json_schema()  # best-effort fallback
    elif cfg.backend_kind == "anthropic":
        kwargs["json_schema"] = change_set_json_schema()
        kwargs["temperature"] = cfg.temperature
    # mock / other: send nothing special; the client returns canned/valid output.

    result = client.complete(messages, **kwargs)
    return validate_change_set(result.text)
