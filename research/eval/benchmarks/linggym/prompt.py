"""Build the prompt for an item at a given information level.

The released benchmark materializes the full **S+G+KP+T** condition, so ``full`` returns
the verbatim prompt (byte-identical to what the official script feeds the model). Lower
levels are reconstructed best-effort from the parsed components for ablations; they are
*close* to the paper's lower-info prompts but not guaranteed byte-identical.
"""

from __future__ import annotations

from .dataset import LingGymItem

LEVELS = ("S", "SG", "SGKP", "SGKPT", "full")
_INSTRUCTION = "Please only return the letter (A–D). Do not say anything else."


def build_prompt(item: LingGymItem, level: str = "full") -> str:
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}, got {level!r}")
    if level in ("full", "SGKPT"):
        # Verbatim released condition — exact replication target.
        return item.prompt_full

    parts = [item.framing, f"Sentence (with missing item): {item.sentence}"]
    if level in ("SG", "SGKP"):
        parts.append(f"Gloss (with missing item): {item.gloss}")
    if level == "SGKP":
        parts.append(
            "Here is a relevant knowledge point for this example, with the related "
            f"morphemes and glosses masked: {item.knowledge_point}"
        )
    parts.append("Options:")
    for letter in ("A", "B", "C", "D"):
        parts.append(item.options.get(letter, f"{letter}:"))
    parts.append(_INSTRUCTION)
    return "\n".join(parts) + "\n"
