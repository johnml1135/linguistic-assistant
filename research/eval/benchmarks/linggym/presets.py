"""Decoding presets for LingGym replication.

The released eval script calls ``model.generate(..., max_new_tokens=512)`` with no
sampling flags — i.e. HuggingFace's default **greedy** decoding. That's deterministic and
reproducible, so ``greedy`` is our faithful default. ``paper`` matches the sampling
settings stated in the paper's appendix (temperature 0.7 / top-p 0.9 / repetition penalty
1.1), seeded for reproducibility.

These ride through the openai_compat adapter into the llama.cpp / vLLM request body. They
do NOT apply to the Anthropic (Opus) endpoint, which rejects sampling params — the runner
drops them there and relies on adaptive thinking.
"""

GREEDY = {"temperature": 0}
PAPER = {"temperature": 0.7, "top_p": 0.9, "repeat_penalty": 1.1, "seed": 0}

PRESETS = {"greedy": GREEDY, "paper": PAPER}
