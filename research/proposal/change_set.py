"""Change-set operation vocabulary, parsing, and strict validation.

The change-set is the product (see repo AGENTS.md / README.md): `lexical/*` ops mirror MiniLcm
vocabulary; `morphophonology/*` ops are our own HC-grammar schema. Every op carries optional
rationale/confidence/impact/provenance. This module validates model output against that contract and
**rejects** anything malformed — it never coerces or silently drops detail.

Stdlib-only (hand-rolled validator) to avoid a jsonschema dependency in the core loop.
"""

from __future__ import annotations

import json
from typing import Any

from .contract import ChangeSet, ValidationFailure

# op type -> required field names (beyond the common optional provenance fields)
OP_TYPES: dict[str, tuple[str, ...]] = {
    # lexical/* (MiniLcm-shaped)
    "lexical.entry.create": ("lexeme_form", "morph_type"),
    "lexical.sense.create": ("entry", "gloss"),
    "lexical.entry.add_allomorph": ("entry", "form"),
    "lexical.entry.set_pos": ("entry", "pos"),
    # morphophonology/* (Hermit Crab constructs)
    "morphophonology.affix.add": ("form", "gram"),
    "morphophonology.allomorph.add": ("morpheme", "form"),
    "morphophonology.rule.add": ("name", "rule"),
    "morphophonology.natural_class.add": ("name", "members"),
    # bilingual/* (cross-lingual sense links — alignment substrate; see research/bilingual/)
    "bilingual.sense_link.add": ("vernacular_sense", "reference_lemma"),
    "bilingual.sense_link.remove": ("vernacular_sense", "reference_lemma"),
}

_COMMON_OPTIONAL = ("rationale", "confidence", "impact", "provenance")

# the field whose value is the op's "key" (for canonical signatures / scoring)
_KEY_FIELD: dict[str, str] = {
    "lexical.entry.create": "lexeme_form",
    "lexical.sense.create": "gloss",
    "lexical.entry.add_allomorph": "form",
    "lexical.entry.set_pos": "entry",
    "morphophonology.affix.add": "form",
    "morphophonology.allomorph.add": "form",
    "morphophonology.rule.add": "name",
    "morphophonology.natural_class.add": "name",
    "bilingual.sense_link.add": "reference_lemma",
    "bilingual.sense_link.remove": "reference_lemma",
}


def _key_str(value: Any) -> str:
    """Normalize a key value (which may be a writing-system dict) to a stable string."""
    if isinstance(value, dict):
        # e.g. {"seh": "kufamba"} -> "seh=kufamba" joined, sorted for stability
        return ";".join(f"{k}={value[k]}" for k in sorted(value))
    return str(value)


def op_signature(op: dict[str, Any]) -> tuple[str, str]:
    """A stable (op_type, key) signature used for set-overlap scoring and dedup."""
    op_type = str(op.get("op", ""))
    key_field = _KEY_FIELD.get(op_type, "")
    return (op_type, _key_str(op.get(key_field, "")))


def _strip_fences(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        # drop the first fence line and a trailing fence
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def validate_change_set(text: str) -> ChangeSet | ValidationFailure:
    """Parse model output into a validated ``ChangeSet`` or a ``ValidationFailure``.

    Accepts either ``{"ops": [...]}`` or a bare ``[...]`` list of ops.
    """
    raw = text or ""
    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        return ValidationFailure(reason=f"not valid JSON: {e}", raw_text=raw)

    if isinstance(data, dict) and "ops" in data:
        ops = data["ops"]
    elif isinstance(data, list):
        ops = data
    else:
        return ValidationFailure(reason="expected an object with 'ops' or a list of ops", raw_text=raw)

    if not isinstance(ops, list):
        return ValidationFailure(reason="'ops' must be a list", raw_text=raw)

    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            return ValidationFailure(reason=f"op[{i}] is not an object", raw_text=raw)
        op_type = op.get("op")
        if op_type not in OP_TYPES:
            return ValidationFailure(reason=f"op[{i}] has unknown op type {op_type!r}", raw_text=raw)
        for field_name in OP_TYPES[op_type]:
            if field_name not in op or op[field_name] in (None, "", [], {}):
                return ValidationFailure(
                    reason=f"op[{i}] ({op_type}) missing required field {field_name!r}", raw_text=raw
                )
        conf = op.get("confidence")
        if conf is not None and not (isinstance(conf, (int, float)) and 0.0 <= float(conf) <= 1.0):
            return ValidationFailure(reason=f"op[{i}] confidence must be in [0,1]", raw_text=raw)

    return ChangeSet(ops=ops)
