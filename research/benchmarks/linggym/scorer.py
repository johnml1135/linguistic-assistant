"""Extract the chosen A-D letter from a model response and score it.

Robust to: a bare ``B``; ``B.``; ``The answer is (C)``; and reasoning/"thinking" text
that ends in a letter. Returns ``None`` when no letter can be found (counted as wrong but
tracked separately as ``unparsed``).
"""

from __future__ import annotations

import re

_EXPLICIT = re.compile(r"(?:answer|option|choice)\s*(?:is|:)?\s*\(?\s*([ABCD])\b", re.I)
_STANDALONE = re.compile(r"\b([ABCD])\b")
# Strip a leading <think>...</think> block (reasoning models) before scanning.
_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)


def extract_letter(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = _THINK.sub(" ", text)
    m = _EXPLICIT.search(cleaned)
    if m:
        return m.group(1).upper()
    matches = _STANDALONE.findall(cleaned.upper())
    return matches[-1] if matches else None  # final standalone letter = the answer


def score(predicted: str | None, gold: str) -> bool:
    return predicted is not None and predicted.upper() == gold.upper()
